import { gaussian } from './random';
import { fillsStarter, positionCap, starterCount, startersFilled } from './roster';
import type { CpuConfig, LeagueConfig, ManagerProfile, Player, Position, RosterSlots } from './types';
import { POSITIONS } from './types';

/**
 * HOW A COMPUTER TEAM PICKS
 *
 * Every available player gets a score in units of draft picks, and the lowest
 * score wins the pick. Starting from ADP and staying in pick units keeps every
 * dial readable: a setting that moves a player by twelve means twelve real
 * picks.
 *
 *   score = biased ADP + a random draw - the roster need bonus + a late
 *           position penalty
 *
 * Position bias moves a player by a share of their ADP plus a flat shift. The
 * share is what makes the dial behave the same at the top and the bottom of the
 * board: pushing running backs up by forty per cent moves the back at pick 60
 * to pick 33 and the back at pick 10 to pick 3. That is what "weigh running
 * backs more heavily" has to mean to stay useful in both places.
 *
 * The random draw is scaled by the standard deviation of the player's real ADP,
 * so the uncertainty sits where real drafts put it. At the default setting of 3
 * the simulator reaches exactly as far as the market does.
 */

/** How far the strongest position setting moves a player, as a share of ADP. */
const BIAS_SHARE = 0.4;
/** The flat part of the position setting, in picks. Keeps the top of the board live. */
const BIAS_FLAT = 2.5;
/** The randomness setting that reproduces real market variance. */
export const MARKET_RANDOMNESS = 3;
/**
 * The furthest ahead of ADP any team will reach, in picks, at randomness 0.
 * Every point of randomness adds to it.
 *
 * Without this floor the deepest players on the board carry a spread wide
 * enough that one draw puts a player nobody drafts into round two. Real rooms
 * reach; they do not reach eighty rounds.
 */
const REACH_BASE = 50;
const REACH_PER_POINT = 12;
/**
 * Two bounds on the random draw, both about keeping the top setting playable
 * rather than merely loud.
 *
 * The floor lets the highest settings shake the top of the board. Spread is
 * measured per player, and the market is so sure about the first few picks that
 * a purely proportional draw would leave round one untouched no matter how far
 * the dial went. The floor only opens above the market setting, so the market
 * setting still reproduces the market exactly.
 *
 * The ceiling stops a player at pick 250 landing in round three.
 */
const NOISE_FLOOR_PER_POINT = 1.2;
const NOISE_CEILING = 60;
/**
 * Manager profiles. A seat with a profile adds its manager's own position dial
 * to the room's, never takes a position earlier than its manager ever has, and
 * leans toward the position and the players its manager keeps coming back to.
 *
 * The round-one lean and the repeat-target pull are in picks, like everything
 * else here. Twelve picks is one round in a twelve-team room: enough to win a
 * close call, not enough to take a round-eight player in round one.
 */
const ROUND_ONE_LEAN = 12;
const REPEAT_TARGET_SHARE = 0.15;
const REPEAT_TARGET_MAX = 12;
/** The pull toward a position once a manager is past his usual round for it. */
const DUE_PULL = 14;
const DUE_PULL_PER_ROUND = 10;
/** The cost of one more QB or TE than a manager usually carries. */
const OVER_HABIT = 12;
const OVER_HABIT_SHARE = 0.35;

const bias = (over: Partial<Record<Position, number>>): Record<Position, number> => ({
  QB: 0, RB: 0, WR: 0, TE: 0, K: 0, DEF: 0, ...over,
});

export function emptyBias(): Record<Position, number> {
  return bias({});
}

export const DEFAULT_CPU: CpuConfig = {
  positionBias: emptyBias(),
  randomness: MARKET_RANDOMNESS,
  needWeight: 5,
  cpuUsesMyRankings: false,
  useManagerProfiles: false,
};

/** One line on how a manager drafts, for the settings screen and the board. */
export function describeProfile(p: ManagerProfile): string {
  const bits: string[] = [];
  const word = (pos: Position) => (pos === 'DEF' ? 'DEF' : pos);
  for (const pos of ['QB', 'TE', 'RB', 'WR'] as Position[]) {
    const v = p.positionBias[pos] ?? 0;
    if (v >= 2) bits.push(word(pos) + ' early');
    else if (v <= -2) bits.push(word(pos) + ' late');
  }
  if (p.roundOneLean) bits.push(p.roundOneLean + ' in round one');
  if (p.medianFirstRound.QB) bits.push('first QB about round ' + Math.round(p.medianFirstRound.QB));
  if (p.repeatTargetNames.length) bits.push('keeps drafting ' + p.repeatTargetNames[0].replace(/ \(\d+\)$/, ''));
  return bits.join(' · ') || 'Drafts close to the room';
}

export interface CpuPreset {
  id: string;
  name: string;
  blurb: string;
  cpu: CpuConfig;
}

export const PRESETS: CpuPreset[] = [
  {
    id: 'market',
    name: 'Market',
    blurb: 'Drafts the board as it stands, with the variance real drafts show.',
    cpu: { ...DEFAULT_CPU },
  },
  {
    id: 'chalk',
    name: 'Chalk',
    blurb: 'Almost no reaching. Shows the earliest a player can fall to you.',
    cpu: { ...DEFAULT_CPU, randomness: 0.5, needWeight: 3 },
  },
  {
    id: 'zero-rb',
    name: 'Zero RB room',
    blurb: 'Receivers and tight ends fly, running backs slide.',
    cpu: { ...DEFAULT_CPU, positionBias: bias({ RB: -4, WR: 3, TE: 2 }) },
  },
  {
    id: 'robust-rb',
    name: 'Robust RB room',
    blurb: 'Running backs go early and often. Tests taking receivers late.',
    cpu: { ...DEFAULT_CPU, positionBias: bias({ RB: 4, WR: -1 }) },
  },
  {
    id: 'early-qb',
    name: 'Quarterback run',
    blurb: 'Quarterbacks come off the board two rounds early.',
    cpu: { ...DEFAULT_CPU, positionBias: bias({ QB: 4 }) },
  },
  {
    id: 'late-qb',
    name: 'Nobody wants a quarterback',
    blurb: 'Quarterbacks slide. Shows what waiting really buys you.',
    cpu: { ...DEFAULT_CPU, positionBias: bias({ QB: -4 }) },
  },
  {
    id: 'chaos',
    name: 'Chaos',
    blurb: 'Triple the normal reach. Every run is a different draft.',
    cpu: { ...DEFAULT_CPU, randomness: 9, needWeight: 4 },
  },
];

/** Move an ADP by one position setting, in the -5 to +5 range. */
export function applyBias(adp: number, level: number): number {
  const tilt = Math.max(-5, Math.min(5, level)) / 5;
  return adp * (1 - BIAS_SHARE * tilt) - BIAS_FLAT * tilt;
}

/** The sentence the settings panel shows under a position slider. */
export function describeBias(level: number, examplePick = 60): string {
  if (level === 0) return 'Follows ADP exactly.';
  const moved = Math.max(1, Math.round(applyBias(examplePick, level)));
  const dir = level > 0 ? 'earlier' : 'later';
  const pct = Math.abs(Math.round(((moved - examplePick) / examplePick) * 100));
  return pct + '% ' + dir + '. Pick ' + examplePick + ' becomes about pick ' + moved + '.';
}

export interface TeamView {
  index: number;
  counts: Record<Position, number>;
  picksMade: number;
}

export interface PickContext {
  league: LeagueConfig;
  cpu: CpuConfig;
  team: TeamView;
  /** The overall number of the pick being made. Bounds how far a team reaches. */
  overallPick: number;
  /** The rank to draft by, per player id. Falls back to the player's ADP. */
  rankOverride?: Map<string, number> | null;
  rng: () => number;
}

/**
 * Score every available player for one computer team and return the best.
 * Returns null only when the pool is empty.
 */
export function chooseCpuPick(available: Player[], ctx: PickContext): Player | null {
  const { league, cpu, team, rng } = ctx;
  const roster: RosterSlots = league.roster;
  const picksLeft = league.rounds - team.picksMade;
  const openStarters = Math.max(0, starterCount(roster) - startersFilled(team.counts, roster));
  const needScale = cpu.needWeight / 5;
  const noiseScale = cpu.randomness / MARKET_RANDOMNESS;
  const reachLimit = ctx.overallPick + REACH_BASE + cpu.randomness * REACH_PER_POINT;
  const noiseFloor = Math.max(0, (cpu.randomness - MARKET_RANDOMNESS) * NOISE_FLOOR_PER_POINT);

  // When a team has exactly as many picks left as it has open starting slots,
  // it stops taking depth. This is a hard rule and not a lean: a roster that
  // cannot field a lineup is not a draft result anybody wants to read.
  const mustFillStarters = needScale > 0 && picksLeft <= openStarters;

  const profile = cpu.useManagerProfiles ? league.teamProfiles?.[team.index] ?? null : null;
  const round = team.picksMade + 1;

  let best: Player | null = null;
  let bestScore = Infinity;

  for (const player of available) {
    const pos = player.position;
    if (player.adp > reachLimit) break; // The pool is in board order.
    if (team.counts[pos] >= positionCap(roster, pos)) continue;

    const fills = fillsStarter(team.counts, roster, pos);
    if (mustFillStarters && !fills) continue;

    // He has never taken his first at this position this early. A hard rule,
    // like the roster caps: it is the one habit six drafts say nothing against.
    const gate = profile?.earliestRound[pos];
    if (gate && round < gate && team.counts[pos] === 0 && !mustFillStarters) continue;

    const base = ctx.rankOverride?.get(player.id) ?? player.adp;
    // His quarterback and tight end dials are measured on the FIRST one he
    // takes, so they only push the first one. Applied to every one, an
    // early-TE manager drafted four tight ends.
    let lean = profile?.positionBias[pos] ?? 0;
    if ((pos === 'QB' || pos === 'TE') && team.counts[pos] > 0) lean = Math.min(lean, 0);
    let level = (cpu.positionBias[pos] ?? 0) + lean;

    // A lean says when he starts looking, not that he never does. From the
    // round he has usually taken his first at a position, a manager who still
    // has none stops leaning away and starts pulling one in. Without this a
    // "waits on quarterback" manager waited until round fifteen every time.
    // Quarterback and tight end only: everybody takes a back and a receiver in
    // the first two rounds, and kickers and defences have their own rule below.
    const due = pos === 'QB' || pos === 'TE' ? profile?.medianFirstRound[pos] : undefined;
    const overdue = due != null && team.counts[pos] === 0 ? round - Math.ceil(due) : -1;
    if (overdue >= 0) level = Math.max(level, 0);

    let score = applyBias(base, level);
    if (overdue >= 0) score -= DUE_PULL + DUE_PULL_PER_ROUND * overdue;

    // Past the number he usually carries at QB or TE, another one costs him a
    // round. A habit, not a cap: a good enough value still gets taken.
    const usual = pos === 'QB' || pos === 'TE' ? profile?.avgCount?.[pos] : undefined;
    // Scaled with the pick: twelve picks is nothing in round fourteen.
    if (usual != null && team.counts[pos] >= Math.max(1, Math.round(usual))) {
      score += Math.max(OVER_HABIT, base * OVER_HABIT_SHARE);
    }

    if (profile) {
      if (round === 1 && profile.roundOneLean === pos) score -= ROUND_ONE_LEAN;
      if (profile.repeatTargets.includes(player.id)) {
        score -= Math.min(REPEAT_TARGET_MAX, base * REPEAT_TARGET_SHARE);
      }
    }

    if (noiseScale > 0) {
      const spread = Math.min(
        NOISE_CEILING,
        Math.max(0.8, player.adpStdev, noiseFloor) * noiseScale,
      );
      score += gaussian(rng, 0, spread);
    }

    if (needScale > 0) {
      const urgency = picksLeft > 0 ? Math.min(1, openStarters / picksLeft) : 1;
      if (fills) score -= needScale * (10 + 28 * urgency);

      // Kickers and defences go in the last two rounds of every real draft, and
      // ADP alone does not enforce that in a short one.
      if ((pos === 'K' || pos === 'DEF') && picksLeft > 2) {
        score += needScale * 45;
      }
    }

    if (score < bestScore) {
      bestScore = score;
      best = player;
    }
  }

  // Every cap is full, or the reach limit left nothing. Take the best player on
  // the board rather than stalling the draft.
  if (!best) return available.length ? available[0] : null;
  return best;
}

export { POSITIONS };
