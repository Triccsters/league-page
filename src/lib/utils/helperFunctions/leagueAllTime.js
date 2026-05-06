import {leagueID} from '$lib/utils/leagueInfo';

let historicalSeasons = [];
try {
    // optional file — only present if league has pre-Sleeper history
    const mod = await import('$lib/utils/historicalSeasons');
    historicalSeasons = mod.historicalSeasons || [];
} catch (e) {
    historicalSeasons = [];
}

const API = (path) => `https://api.sleeper.app/v1${path}`;

const fetchJSON = async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
};

const fetchSeason = async (lid) => {
    const [league, users, rosters, winnersBracket] = await Promise.all([
        fetchJSON(API(`/league/${lid}`)),
        fetchJSON(API(`/league/${lid}/users`)),
        fetchJSON(API(`/league/${lid}/rosters`)),
        fetchJSON(API(`/league/${lid}/winners_bracket`)).catch(() => []),
    ]);

    // Fetch all weekly matchups (until empty)
    const matchupsByWeek = {};
    for (let week = 1; week <= 18; week++) {
        try {
            const mws = await fetchJSON(API(`/league/${lid}/matchups/${week}`));
            if (!mws || mws.length === 0) break;
            const hasPoints = mws.some(m => (m.points || 0) > 0);
            if (!hasPoints) break;
            matchupsByWeek[week] = mws;
        } catch (e) {
            break;
        }
    }

    return { league, users, rosters, matchupsByWeek, winnersBracket, league_id: lid };
};

const walkLeagueChain = async () => {
    const seasons = [];
    let currentId = leagueID;
    let safety = 0;
    while (currentId && safety < 30) {
        const data = await fetchSeason(currentId);
        seasons.push(data);
        currentId = data.league.previous_league_id;
        safety++;
    }
    // Oldest to newest
    return seasons.reverse();
};

const ridToOwner = (rosters) => Object.fromEntries(rosters.map(r => [r.roster_id, r.owner_id]));
const userById = (users) => Object.fromEntries(users.map(u => [u.user_id, u]));

const findChampion = (winnersBracket, ridToOwnerMap, userMap) => {
    if (!winnersBracket || winnersBracket.length === 0) return null;
    // Final = highest round, championship match (m=1 or first matchup of last round)
    const maxRound = Math.max(...winnersBracket.map(g => g.r || 0));
    const finals = winnersBracket.filter(g => g.r === maxRound);
    if (finals.length === 0) return null;
    // Among finals, find the championship game (lowest m typically)
    const champGame = finals.sort((a, b) => (a.m || 0) - (b.m || 0))[0];
    if (!champGame.w) return null;
    const champRid = champGame.w;
    const ownerId = ridToOwnerMap[champRid];
    const u = userMap[ownerId];
    return {
        roster_id: champRid,
        owner_id: ownerId,
        manager: u?.display_name || `Roster ${champRid}`,
        team: u?.metadata?.team_name || u?.display_name || `Team ${champRid}`,
        runner_up_rid: champGame.l,
    };
};

export const getAllTimeStats = async () => {
    const seasons = await walkLeagueChain();
    if (seasons.length === 0) {
        return { error: 'No seasons found' };
    }

    // Per-manager aggregates keyed by user_id
    const mgr = {}; // user_id -> { display_name, team_names: Set, seasons: Set, wins, losses, ties, points_for, points_against, championships, runner_ups, biggest_score, biggest_blowout_win, biggest_loss }
    const ensure = (uid, displayName) => {
        if (!mgr[uid]) {
            mgr[uid] = {
                user_id: uid,
                display_name: displayName,
                team_names: new Set(),
                seasons: new Set(),
                wins: 0, losses: 0, ties: 0,
                points_for: 0, points_against: 0,
                championships: 0, runner_ups: 0,
                biggest_score: { points: 0 },
                biggest_blowout_win: { margin: 0 },
                biggest_loss: { margin: 0 },
            };
        }
        return mgr[uid];
    };

    const champions = []; // per-season list
    const allMatchupsFlat = []; // for blowout/closest

    for (const s of seasons) {
        const r2o = ridToOwner(s.rosters);
        const uMap = userById(s.users);

        // Identify champion + runner-up
        const champ = findChampion(s.winnersBracket, r2o, uMap);
        if (champ) {
            const cm = ensure(champ.owner_id, champ.manager);
            cm.championships += 1;
            const runnerOwnerId = r2o[champ.runner_up_rid];
            if (runnerOwnerId) {
                const ru = uMap[runnerOwnerId];
                ensure(runnerOwnerId, ru?.display_name || 'Unknown').runner_ups += 1;
            }
            champions.push({
                season: s.league.season,
                league_name: s.league.name,
                champion: champ.manager,
                champion_team: champ.team,
                runner_up: runnerOwnerId ? (uMap[runnerOwnerId]?.display_name || 'Unknown') : '—',
            });
        }

        // Walk weekly matchups, aggregate
        for (const week of Object.keys(s.matchupsByWeek)) {
            const mws = s.matchupsByWeek[week];
            // Pair by matchup_id for h2h
            const byMid = {};
            for (const m of mws) {
                const mid = m.matchup_id;
                if (mid == null) continue;
                (byMid[mid] = byMid[mid] || []).push(m);
            }
            for (const [mid, sides] of Object.entries(byMid)) {
                if (sides.length !== 2) continue;
                const [a, b] = sides.sort((x, y) => (y.points || 0) - (x.points || 0));
                const aOwner = r2o[a.roster_id];
                const bOwner = r2o[b.roster_id];
                if (!aOwner || !bOwner) continue;
                const aMgr = ensure(aOwner, uMap[aOwner]?.display_name || 'Unknown');
                const bMgr = ensure(bOwner, uMap[bOwner]?.display_name || 'Unknown');
                aMgr.seasons.add(s.league.season);
                bMgr.seasons.add(s.league.season);
                if (uMap[aOwner]?.metadata?.team_name) aMgr.team_names.add(uMap[aOwner].metadata.team_name);
                if (uMap[bOwner]?.metadata?.team_name) bMgr.team_names.add(uMap[bOwner].metadata.team_name);

                const aPts = a.points || 0;
                const bPts = b.points || 0;
                aMgr.points_for += aPts; aMgr.points_against += bPts;
                bMgr.points_for += bPts; bMgr.points_against += aPts;
                if (aPts > bPts) { aMgr.wins++; bMgr.losses++; }
                else if (aPts < bPts) { aMgr.losses++; bMgr.wins++; }
                else { aMgr.ties++; bMgr.ties++; }

                const margin = Math.abs(aPts - bPts);
                if (aPts > aMgr.biggest_score.points) aMgr.biggest_score = { points: aPts, season: s.league.season, week: Number(week) };
                if (bPts > bMgr.biggest_score.points) bMgr.biggest_score = { points: bPts, season: s.league.season, week: Number(week) };
                if (margin > aMgr.biggest_blowout_win.margin && aPts > bPts) aMgr.biggest_blowout_win = { margin, vs: bMgr.display_name, season: s.league.season, week: Number(week) };
                if (margin > bMgr.biggest_loss.margin && aPts > bPts) bMgr.biggest_loss = { margin, vs: aMgr.display_name, season: s.league.season, week: Number(week) };

                allMatchupsFlat.push({
                    season: s.league.season,
                    week: Number(week),
                    winner: aMgr.display_name,
                    loser: bMgr.display_name,
                    winner_pts: Number(aPts.toFixed(2)),
                    loser_pts: Number(bPts.toFixed(2)),
                    margin: Number(margin.toFixed(2)),
                });
            }
        }
    }

    // Build manager rows
    const managerRows = Object.values(mgr).map(m => {
        const games = m.wins + m.losses + m.ties;
        const winPct = games ? (m.wins + 0.5 * m.ties) / games : 0;
        return {
            manager: m.display_name,
            team_names: [...m.team_names].slice(0, 3).join(' / '),
            seasons_played: m.seasons.size,
            wins: m.wins,
            losses: m.losses,
            ties: m.ties,
            win_pct: Number(winPct.toFixed(4)),
            points_for: Number(m.points_for.toFixed(2)),
            points_against: Number(m.points_against.toFixed(2)),
            championships: m.championships,
            runner_ups: m.runner_ups,
            biggest_score: m.biggest_score.points ? `${m.biggest_score.points.toFixed(2)} (${m.biggest_score.season} W${m.biggest_score.week})` : '—',
        };
    });
    managerRows.sort((a, b) => b.championships - a.championships || b.win_pct - a.win_pct);
    managerRows.forEach((row, i) => row.rank = i + 1);

    // All-time records
    const sorted = [...allMatchupsFlat];
    sorted.sort((a, b) => b.margin - a.margin);
    const biggestBlowouts = sorted.slice(0, 5);
    const closestGames = [...sorted].reverse().slice(0, 5);
    const highestScores = [...allMatchupsFlat]
        .map(m => [{ team: m.winner, pts: m.winner_pts, season: m.season, week: m.week }, { team: m.loser, pts: m.loser_pts, season: m.season, week: m.week }])
        .flat()
        .sort((a, b) => b.pts - a.pts)
        .slice(0, 5);

    // Merge in any manually-curated historical (pre-Sleeper) seasons.
    const historicalChampions = historicalSeasons.map(s => ({
        season: String(s.season),
        league_name: s.league_name || seasons[seasons.length - 1].league.name,
        champion: s.champion?.manager || s.champion?.team || '—',
        champion_team: s.champion?.team || '—',
        runner_up: s.runner_up?.manager || s.runner_up?.team || '—',
        platform: s.platform || 'historical',
        notes: s.notes || '',
    }));

    const sleeperChampions = champions.map(c => ({ ...c, platform: 'sleeper' }));
    const allChampions = [...sleeperChampions, ...historicalChampions]
        .sort((a, b) => Number(b.season) - Number(a.season));

    const allSeasonNumbers = allChampions.map(c => Number(c.season)).filter(n => !isNaN(n));
    const seasonRange = allSeasonNumbers.length
        ? `${Math.min(...allSeasonNumbers)}–${Math.max(...allSeasonNumbers)}`
        : `${seasons[0].league.season}–${seasons[seasons.length - 1].league.season}`;

    return {
        seasons_count: seasons.length + historicalSeasons.length,
        season_range: seasonRange,
        league_name_current: seasons[seasons.length - 1].league.name,
        champions: allChampions,
        manager_rows: managerRows,
        biggest_blowouts: biggestBlowouts,
        closest_games: closestGames,
        highest_scores: highestScores,
    };
};
