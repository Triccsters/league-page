// The read-outs the draft room shows beside the board: who picks before you
// are up again, what they need, what they usually do here, and what the room
// is likely to take off the board in that stretch.
import { currentPick, currentTeam, draftPlayer, runCpuPick } from './draft';
import { fillsStarter } from './roster';

export const POS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];

/** Starting slots this roster could still fill, by position. K and DEF only late. */
export function openNeeds(counts, roster, round, rounds) {
    return POS.filter((p) => {
        if ((p === 'K' || p === 'DEF') && round < rounds - 3) return false;
        return fillsStarter(counts, roster, p);
    });
}

/** Repeat targets of a manager that are still on the board. */
export function repeatsAvailable(profile, engine) {
    if (!profile?.repeatTargets?.length) return [];
    const avail = new Set(engine.state.availableIds);
    const out = [];
    profile.repeatTargets.forEach((id, i) => {
        const hit = [id, 'sl-' + id].find((x) => avail.has(x));
        if (hit) out.push({ id: hit, label: profile.repeatTargetNames?.[i] || engine.byId.get(hit)?.name });
    });
    return out;
}

/** What a manager usually does at this point, in a few words. */
export function habitNow(profile, counts, round) {
    if (!profile) return 'No draft history here, drafts the board';
    const notes = [];
    for (const p of ['QB', 'TE']) {
        const med = profile.medianFirstRound?.[p];
        if (counts[p] || med == null) continue;
        const usual = Math.round(med);
        if (round >= usual) notes.push(`due at ${p} (usually round ${usual})`);
        else if (usual - round <= 1) notes.push(`${p} soon (usually round ${usual})`);
    }
    if (round === 1 && profile.roundOneLean) notes.push(`takes a ${profile.roundOneLean} in round one`);
    if (profile.drafts && profile.drafts < 3) notes.push(`thin history, ${profile.drafts} draft${profile.drafts === 1 ? '' : 's'}`);
    return notes.join(', ');
}

/**
 * Play the picks between now and your next one many times over.
 *
 * Each run gets its own seed, so the computer seats roll new dice but keep
 * their habits. If you are on the clock, your own pick is spent on the last
 * player on the board, so the odds read as "if you pass on him now".
 */
export function simulateWindow(engine, untilPick, sims = 120) {
    const start = engine.state;
    const teamPos = new Map(); // team index -> pos -> count
    const posTaken = Object.fromEntries(POS.map((p) => [p, 0]));
    const posAny = Object.fromEntries(POS.map((p) => [p, 0]));
    const gone = new Map(); // player id -> runs he was taken in
    let runs = 0;
    for (let s = 0; s < sims; s += 1) {
        let e = { ...engine, state: { ...start, league: { ...start.league, seed: (start.league.seed + (s + 1) * 104729) >>> 0 } } };
        const seen = new Set();
        let guard = 0;
        while (!e.state.done && currentPick(e.state) < untilPick && guard < 400) {
            guard += 1;
            const team = currentTeam(e.state);
            if (team?.isUser) {
                const ids = e.state.availableIds;
                e = draftPlayer(e, ids[ids.length - 1]);
                continue;
            }
            e = runCpuPick(e);
            const last = e.state.picks[e.state.picks.length - 1];
            const pl = e.byId.get(last.playerId);
            if (!pl) continue;
            const m = teamPos.get(last.teamIndex) || {};
            m[pl.position] = (m[pl.position] || 0) + 1;
            teamPos.set(last.teamIndex, m);
            posTaken[pl.position] += 1;
            seen.add(pl.position);
            gone.set(pl.id, (gone.get(pl.id) || 0) + 1);
        }
        for (const p of seen) posAny[p] += 1;
        runs += 1;
    }
    // Share of that team's picks in this stretch going to each position.
    const lean = (i, picks = 1) => {
        const m = teamPos.get(i) || {};
        return POS.map((p) => ({ p, share: (m[p] || 0) / (runs * picks) }))
            .filter((x) => x.share >= 0.15).sort((a, b) => b.share - a.share);
    };
    return {
        runs,
        lean,
        expected: Object.fromEntries(POS.map((p) => [p, posTaken[p] / runs])),
        anyTaken: Object.fromEntries(POS.map((p) => [p, posAny[p] / runs])),
        survives: (id) => 1 - (gone.get(id) || 0) / runs,
    };
}

/**
 * How this league has really drafted in a stretch of rounds, against what the
 * current board's ADP would hand out over the same picks.
 */
export function areaMix(roundMix, players, teams, fromRound, toRound) {
    if (!roundMix) return null;
    const real = Object.fromEntries(POS.map((p) => [p, 0]));
    let n = 0;
    for (let r = fromRound; r <= toRound; r += 1) {
        const m = roundMix.rounds[r - 1];
        if (!m) continue;
        for (const p of POS) { real[p] += m[p]; n += m[p]; }
    }
    if (!n) return null;
    const board = [...players].sort((a, b) => a.adp - b.adp).slice((fromRound - 1) * teams, toRound * teams);
    const adp = Object.fromEntries(POS.map((p) => [p, 0]));
    for (const pl of board) if (adp[pl.position] != null) adp[pl.position] += 1;
    const rows = POS.map((p) => ({ p, real: real[p] / n, adp: board.length ? adp[p] / board.length : 0 }))
        .filter((r) => r.real >= 0.02 || r.adp >= 0.02);
    const gap = [...rows].sort((a, b) => Math.abs(b.real - b.adp) - Math.abs(a.real - a.adp))[0];
    return { rows, gap, seasons: roundMix.seasons, fromRound, toRound };
}
