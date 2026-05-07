import {leagueID} from '$lib/utils/leagueInfo';
import {historicalSeasons} from '$lib/utils/historicalSeasons';

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

    // Aggregate Yahoo-era manager stats by canonical manager name.
    const yahooMgr = {};
    const ensureYM = (name) => {
        if (!yahooMgr[name]) {
            yahooMgr[name] = {
                manager: name,
                seasons_played: 0,
                wins: 0, losses: 0, ties: 0,
                points_for: 0, points_against: 0,
                championships: 0, runner_ups: 0, third_places: 0,
                team_names: new Set(),
            };
        }
        return yahooMgr[name];
    };
    for (const s of historicalSeasons) {
        const champMgr = s.champion?.manager;
        const ruMgr = s.runner_up?.manager;
        const thirdMgr = s.third_place?.manager;
        if (champMgr && champMgr !== '—' && champMgr !== '(hidden)') {
            ensureYM(champMgr).championships += 1;
            ensureYM(champMgr).team_names.add(s.champion.team);
        }
        if (ruMgr && ruMgr !== '—' && ruMgr !== '(hidden)') ensureYM(ruMgr).runner_ups += 1;
        if (thirdMgr && thirdMgr !== '—' && thirdMgr !== '(hidden)') ensureYM(thirdMgr).third_places += 1;
        for (const row of (s.final_standings || [])) {
            const m = row.manager;
            if (!m || m === '—' || m === '(hidden)') continue;
            const ym = ensureYM(m);
            ym.seasons_played += 1;
            ym.wins += row.wins || 0;
            ym.losses += row.losses || 0;
            ym.ties += row.ties || 0;
            ym.points_for += row.points_for || 0;
            ym.points_against += row.points_against || 0;
            if (row.team) ym.team_names.add(row.team);
        }
    }
    const yahooMgrRows = Object.values(yahooMgr).map(m => {
        const games = m.wins + m.losses + m.ties;
        return {
            manager: m.manager,
            seasons_played: m.seasons_played,
            wins: m.wins, losses: m.losses, ties: m.ties,
            win_pct: games ? Number(((m.wins + 0.5 * m.ties) / games).toFixed(4)) : 0,
            points_for: Number(m.points_for.toFixed(2)),
            points_against: Number(m.points_against.toFixed(2)),
            championships: m.championships,
            runner_ups: m.runner_ups,
            third_places: m.third_places,
            team_names: [...m.team_names].slice(0, 4).join(' / '),
        };
    });
    yahooMgrRows.sort((a, b) => b.championships - a.championships || b.win_pct - a.win_pct);
    yahooMgrRows.forEach((r, i) => r.rank = i + 1);

    // T.J.'s per-season Sleeper data — find his roster each year and pull W-L
    const TJ_PATTERN = /^(triccster|trickster|t\.?j\.?r?|trick)$/i;
    const tjSleeperSeasons = [];
    let tjUserId = null;
    for (const s of seasons) {
        const uMap = userById(s.users);
        // Find T.J.'s user_id (stable across seasons in Sleeper)
        if (!tjUserId) {
            for (const u of s.users) {
                if (TJ_PATTERN.test(u.display_name || '')) {
                    tjUserId = u.user_id;
                    break;
                }
            }
        }
        if (!tjUserId) continue;
        const tjRoster = s.rosters.find(r => r.owner_id === tjUserId);
        if (!tjRoster) continue;
        const u = uMap[tjUserId];
        const settings = tjRoster.settings || {};
        // Determine playoff finish from winners_bracket
        let finish = '—';
        const champ = findChampion(s.winnersBracket, ridToOwner(s.rosters), uMap);
        if (champ) {
            if (champ.roster_id === tjRoster.roster_id) finish = 'Champion 🏆';
            else if (champ.runner_up_rid === tjRoster.roster_id) finish = 'Runner-up';
        }
        if (finish === '—' && settings.rank != null) finish = `${settings.rank}`;

        tjSleeperSeasons.push({
            season: String(s.league.season),
            team: u?.metadata?.team_name || u?.display_name || '—',
            wins: settings.wins ?? null,
            losses: settings.losses ?? null,
            ties: settings.ties ?? 0,
            points_for: settings.fpts != null ? Number(`${settings.fpts}.${settings.fpts_decimal ?? 0}`) : null,
            points_against: settings.fpts_against != null ? Number(`${settings.fpts_against}.${settings.fpts_against_decimal ?? 0}`) : null,
            finish,
            platform: 'sleeper',
        });
    }
    tjSleeperSeasons.sort((a, b) => Number(b.season) - Number(a.season));

    const tjFromSleeper = managerRows.find(m => /trick|triccster/i.test(m.manager));
    const tjFromYahoo = historicalSeasons
        .filter(s => (s.final_standings || []).some(r => r.manager === 'T.J.') || s.runner_up?.manager === 'T.J.')
        .map(s => {
            const row = (s.final_standings || []).find(r => r.manager === 'T.J.');
            const isRunnerUp = s.runner_up?.manager === 'T.J.';
            return {
                season: s.season,
                team: row?.team || s.runner_up?.team || '—',
                rank: row?.rank,
                wins: row?.wins,
                losses: row?.losses,
                ties: row?.ties,
                finished: isRunnerUp ? 'Runner-up' : (row?.rank ? `${row.rank}` : '—'),
                platform: 'yahoo',
            };
        }).sort((a, b) => Number(b.season) - Number(a.season));

    // Sleeper-era records (computed from matchup data)
    const sleeperRecords = (() => {
        const allWeekScores = [];  // {team, manager, points, season, week, opponent_points, opponent_team, margin}
        const seasonTotals = {};   // rid+season -> { points, team, manager, season }

        for (const s of seasons) {
            const r2o = ridToOwner(s.rosters);
            const uMap = userById(s.users);
            const teamFor = (rid) => {
                const u = uMap[r2o[rid]];
                return u?.metadata?.team_name || u?.display_name || `Team ${rid}`;
            };
            const mgrFor = (rid) => {
                const u = uMap[r2o[rid]];
                return u?.display_name || '—';
            };
            for (const week of Object.keys(s.matchupsByWeek)) {
                const mws = s.matchupsByWeek[week];
                const byMid = {};
                for (const m of mws) (byMid[m.matchup_id] = byMid[m.matchup_id] || []).push(m);
                for (const sides of Object.values(byMid)) {
                    if (sides.length !== 2) continue;
                    const [a, b] = sides;
                    const ap = a.points || 0, bp = b.points || 0;
                    allWeekScores.push({
                        team: teamFor(a.roster_id), manager: mgrFor(a.roster_id),
                        points: Number(ap.toFixed(2)),
                        opp_team: teamFor(b.roster_id), opp_points: Number(bp.toFixed(2)),
                        season: s.league.season, week: Number(week),
                        margin: Number((ap - bp).toFixed(2)),
                    });
                    allWeekScores.push({
                        team: teamFor(b.roster_id), manager: mgrFor(b.roster_id),
                        points: Number(bp.toFixed(2)),
                        opp_team: teamFor(a.roster_id), opp_points: Number(ap.toFixed(2)),
                        season: s.league.season, week: Number(week),
                        margin: Number((bp - ap).toFixed(2)),
                    });
                    const aKey = `${a.roster_id}-${s.league.season}`;
                    const bKey = `${b.roster_id}-${s.league.season}`;
                    seasonTotals[aKey] = seasonTotals[aKey] || { points: 0, team: teamFor(a.roster_id), manager: mgrFor(a.roster_id), season: s.league.season };
                    seasonTotals[bKey] = seasonTotals[bKey] || { points: 0, team: teamFor(b.roster_id), manager: mgrFor(b.roster_id), season: s.league.season };
                    seasonTotals[aKey].points += ap;
                    seasonTotals[bKey].points += bp;
                }
            }
        }
        const sortedHigh = [...allWeekScores].sort((x, y) => y.points - x.points);
        const sortedLow = allWeekScores.filter(x => x.points > 0).sort((x, y) => x.points - y.points);
        const sortedMargin = allWeekScores.filter(x => x.margin > 0).sort((x, y) => y.margin - x.margin);
        const sortedClosest = allWeekScores.filter(x => x.margin > 0).sort((x, y) => x.margin - y.margin);
        const seasonHigh = Object.values(seasonTotals).sort((x, y) => y.points - x.points);
        const seasonLow = Object.values(seasonTotals).filter(x => x.points > 0).sort((x, y) => x.points - y.points);

        return {
            highest_single_week: sortedHigh.slice(0, 5).map(x => ({ holder: x.team, opponent: x.opp_team, value: x.points, season: x.season, week: x.week })),
            lowest_single_week: sortedLow.slice(0, 5).map(x => ({ holder: x.team, opponent: x.opp_team, value: x.points, season: x.season, week: x.week })),
            biggest_blowouts: sortedMargin.slice(0, 5).map(x => ({ holder: x.team, opponent: x.opp_team, value: x.margin, season: x.season, week: x.week })),
            closest_games: sortedClosest.slice(0, 5).map(x => ({ holder: x.team, opponent: x.opp_team, value: x.margin, season: x.season, week: x.week })),
            highest_season: seasonHigh.slice(0, 5).map(x => ({ holder: x.team, value: Number(x.points.toFixed(2)), season: x.season })),
            lowest_season: seasonLow.slice(0, 5).map(x => ({ holder: x.team, value: Number(x.points.toFixed(2)), season: x.season })),
        };
    })();

    return {
        seasons_count: seasons.length + historicalSeasons.length,
        season_range: seasonRange,
        league_name_current: seasons[seasons.length - 1].league.name,
        champions: allChampions,
        manager_rows: managerRows,
        yahoo_manager_rows: yahooMgrRows,
        biggest_blowouts: biggestBlowouts,
        closest_games: closestGames,
        highest_scores: highestScores,
        tj_career_yahoo: tjFromYahoo,
        tj_career_sleeper: tjFromSleeper,
        tj_sleeper_seasons: tjSleeperSeasons,
        tj_combined_career: (() => {
            // Yahoo aggregates from final_standings (skips seasons without W-L data, like 2011)
            let yW = 0, yL = 0, yT = 0, yPF = 0, yPA = 0, ySeasons = 0;
            let yChamps = 0, yRunner = 0, yThird = 0;
            for (const s of historicalSeasons) {
                const row = (s.final_standings || []).find(r => r.manager === 'T.J.');
                if (row) {
                    ySeasons += 1;
                    yW += row.wins || 0;
                    yL += row.losses || 0;
                    yT += row.ties || 0;
                    yPF += row.points_for || 0;
                    yPA += row.points_against || 0;
                }
                if (s.champion?.manager === 'T.J.') yChamps += 1;
                if (s.runner_up?.manager === 'T.J.') yRunner += 1;
                if (s.third_place?.manager === 'T.J.') yThird += 1;
            }

            // Sleeper aggregates from per-season rows
            let sW = 0, sL = 0, sT = 0, sPF = 0, sPA = 0, sSeasons = 0;
            let sChamps = 0, sRunner = 0;
            for (const ss of tjSleeperSeasons) {
                sSeasons += 1;
                sW += ss.wins || 0;
                sL += ss.losses || 0;
                sT += ss.ties || 0;
                sPF += ss.points_for || 0;
                sPA += ss.points_against || 0;
                if (ss.finish === 'Champion 🏆') sChamps += 1;
                if (ss.finish === 'Runner-up') sRunner += 1;
            }

            const tW = yW + sW, tL = yL + sL, tT = yT + sT;
            const tGames = tW + tL + tT;
            return {
                yahoo: { seasons: ySeasons, wins: yW, losses: yL, ties: yT, points_for: yPF, points_against: yPA, championships: yChamps, runner_ups: yRunner, third_places: yThird },
                sleeper: { seasons: sSeasons, wins: sW, losses: sL, ties: sT, points_for: sPF, points_against: sPA, championships: sChamps, runner_ups: sRunner },
                combined: {
                    seasons: ySeasons + sSeasons,
                    wins: tW, losses: tL, ties: tT,
                    win_pct: tGames ? Number(((tW + 0.5 * tT) / tGames).toFixed(4)) : 0,
                    points_for: Number((yPF + sPF).toFixed(2)),
                    points_against: Number((yPA + sPA).toFixed(2)),
                    championships: yChamps + sChamps,
                    runner_ups: yRunner + sRunner,
                    third_places: yThird,
                    finals_appearances: yChamps + yRunner + sChamps + sRunner,
                },
            };
        })(),
        sleeper_records: sleeperRecords,
    };
};
