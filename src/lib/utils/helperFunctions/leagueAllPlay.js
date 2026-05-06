import {leagueID} from '$lib/utils/leagueInfo';

const FLEX_ELIGIBLE = new Set(['RB', 'WR', 'TE']);
const SUPER_FLEX_ELIGIBLE = new Set(['QB', 'RB', 'WR', 'TE']);

let _playersCache = null;

const fetchJSON = async (path) => {
    const r = await fetch(`https://api.sleeper.app/v1/league/${leagueID}${path}`);
    if (!r.ok) throw new Error(`Sleeper API ${path}: ${r.status}`);
    return r.json();
};

const fetchPlayers = async () => {
    if (_playersCache) return _playersCache;
    const r = await fetch('https://api.sleeper.app/v1/players/nfl');
    if (!r.ok) throw new Error('failed to fetch player metadata');
    const raw = await r.json();
    _playersCache = {};
    for (const [pid, p] of Object.entries(raw)) {
        if (p.position) {
            _playersCache[pid] = { position: p.position };
        }
    }
    return _playersCache;
};

const fetchAllMatchups = async (maxWeek = 18) => {
    const matchupsByWeek = {};
    for (let week = 1; week <= maxWeek; week++) {
        try {
            const mws = await fetchJSON(`/matchups/${week}`);
            if (!mws || mws.length === 0) break;
            const hasPoints = mws.some(m => (m.points || 0) > 0);
            if (!hasPoints) break;
            matchupsByWeek[week] = mws;
        } catch (e) {
            break;
        }
    }
    return matchupsByWeek;
};

const buildRosterMeta = (users, rosters) => {
    const userById = Object.fromEntries(users.map(u => [u.user_id, u]));
    const meta = {};
    for (const r of rosters) {
        const u = userById[r.owner_id];
        meta[r.roster_id] = {
            owner_id: r.owner_id,
            display_name: u?.display_name || `Roster ${r.roster_id}`,
            team_name: u?.metadata?.team_name || u?.display_name || `Team ${r.roster_id}`,
            avatar: u?.avatar,
        };
    }
    return meta;
};

export const getAllPlayStandings = async () => {
    const [league, users, rosters] = await Promise.all([
        fetchJSON(''),
        fetchJSON('/users'),
        fetchJSON('/rosters'),
    ]);
    const matchupsByWeek = await fetchAllMatchups();
    const rosterMeta = buildRosterMeta(users, rosters);

    const wins = {};
    const losses = {};
    const ties = {};
    const pointsFor = {};
    for (const rid of Object.keys(rosterMeta)) {
        wins[rid] = 0; losses[rid] = 0; ties[rid] = 0; pointsFor[rid] = 0;
    }

    const weeks = Object.keys(matchupsByWeek).map(Number).sort((a, b) => a - b);
    for (const week of weeks) {
        const scores = {};
        for (const m of matchupsByWeek[week]) {
            scores[m.roster_id] = m.points || 0;
            pointsFor[m.roster_id] = (pointsFor[m.roster_id] || 0) + (m.points || 0);
        }
        const ridList = Object.keys(scores);
        for (const rid of ridList) {
            for (const other of ridList) {
                if (rid === other) continue;
                if (scores[rid] > scores[other]) wins[rid]++;
                else if (scores[rid] < scores[other]) losses[rid]++;
                else ties[rid]++;
            }
        }
    }

    const out = Object.keys(rosterMeta).map(rid => {
        const w = wins[rid], l = losses[rid], t = ties[rid];
        const games = w + l + t;
        const pct = games ? (w + 0.5 * t) / games : 0;
        return {
            roster_id: Number(rid),
            team: rosterMeta[rid].team_name,
            manager: rosterMeta[rid].display_name,
            avatar: rosterMeta[rid].avatar,
            all_play_w: w,
            all_play_l: l,
            all_play_t: t,
            all_play_pct: Number(pct.toFixed(4)),
            points_for: Number(pointsFor[rid].toFixed(2)),
        };
    });
    out.sort((a, b) => b.all_play_pct - a.all_play_pct || b.points_for - a.points_for);
    out.forEach((row, i) => row.rank = i + 1);
    return {
        rows: out,
        weeksIncluded: weeks,
        season: league.season,
        leagueName: league.name,
    };
};

const optimalLineupPoints = (playerPoints, players, rosterPositions) => {
    const byPos = {};
    for (const [pid, pts] of Object.entries(playerPoints)) {
        const pos = players[pid]?.position;
        if (!pos) continue;
        (byPos[pos] = byPos[pos] || []).push({ pts: Number(pts) || 0, pid });
    }
    for (const pos of Object.keys(byPos)) byPos[pos].sort((a, b) => b.pts - a.pts);

    const used = new Set();
    let total = 0;

    const popBest = (positions) => {
        let best = 0, bestPid = null;
        for (const pos of positions) {
            const pool = byPos[pos] || [];
            for (const { pts, pid } of pool) {
                if (used.has(pid)) continue;
                if (pts > best) { best = pts; bestPid = pid; }
                break;
            }
        }
        if (bestPid) used.add(bestPid);
        return best;
    };

    for (const slot of rosterPositions) {
        if (slot === 'BN' || slot === 'IR' || slot === 'TAXI') continue;
        if (slot === 'FLEX') total += popBest(FLEX_ELIGIBLE);
        else if (slot === 'SUPER_FLEX') total += popBest(SUPER_FLEX_ELIGIBLE);
        else if (slot === 'REC_FLEX') total += popBest(new Set(['WR', 'TE']));
        else total += popBest(new Set([slot]));
    }
    return Number(total.toFixed(2));
};

export const getLineupEfficiency = async () => {
    const [league, users, rosters] = await Promise.all([
        fetchJSON(''),
        fetchJSON('/users'),
        fetchJSON('/rosters'),
    ]);
    const [matchupsByWeek, players] = await Promise.all([
        fetchAllMatchups(),
        fetchPlayers(),
    ]);
    const rosterMeta = buildRosterMeta(users, rosters);
    const rosterPositions = league.roster_positions || [];

    const actualByRid = {};
    const optimalByRid = {};
    const weeksByRid = {};

    const weeks = Object.keys(matchupsByWeek).map(Number).sort((a, b) => a - b);
    for (const week of weeks) {
        for (const m of matchupsByWeek[week]) {
            const rid = m.roster_id;
            const actual = m.points || 0;
            actualByRid[rid] = (actualByRid[rid] || 0) + actual;
            let pp = m.players_points;
            if (!pp || Object.keys(pp).length === 0) {
                pp = {};
                const starters = m.starters || [];
                const sp = m.starters_points || [];
                for (let i = 0; i < starters.length; i++) pp[starters[i]] = sp[i] || 0;
            }
            const optimal = optimalLineupPoints(pp, players, rosterPositions);
            optimalByRid[rid] = (optimalByRid[rid] || 0) + optimal;
            weeksByRid[rid] = (weeksByRid[rid] || 0) + 1;
        }
    }

    const out = Object.keys(rosterMeta).map(rid => {
        const actual = Number((actualByRid[rid] || 0).toFixed(2));
        const optimal = Number((optimalByRid[rid] || 0).toFixed(2));
        const eff = optimal ? Number((actual / optimal * 100).toFixed(1)) : 0;
        return {
            roster_id: Number(rid),
            team: rosterMeta[rid].team_name,
            manager: rosterMeta[rid].display_name,
            avatar: rosterMeta[rid].avatar,
            actual_points: actual,
            optimal_points: optimal,
            points_left_on_bench: Number((optimal - actual).toFixed(2)),
            efficiency_pct: eff,
            weeks_played: weeksByRid[rid] || 0,
        };
    });
    out.sort((a, b) => b.efficiency_pct - a.efficiency_pct);
    out.forEach((row, i) => row.rank = i + 1);
    return {
        rows: out,
        weeksIncluded: weeks,
        season: league.season,
        leagueName: league.name,
    };
};
