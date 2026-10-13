import { leagueID, shimmed } from "$lib/utils/leagueInfo"
import { round } from "$lib/utils/helperFunctions/universalFunctions"
import { waitForAll } from "$lib/utils/helperFunctions/multiPromise"
import { json, error } from '@sveltejs/kit';

export async function GET({ url }) {
    // get NFL state from sleeper (week and year)
    // hooks.client.js redirects Sleeper league/draft calls to the baked shim,
    // but it is a CLIENT hook and this endpoint runs on the server. Without
    // these two, a shimmed (ESPN) league id is sent to api.sleeper.app, which
    // has no such league, and the whole endpoint 500s.
    const leagueUrl = shimmed
        ? `${url.origin}/shim/v1/league/${leagueID}.json`
        : `https://api.sleeper.app/v1/league/${leagueID}`;
    const bracketUrl = shimmed
        ? `${url.origin}/shim/v1/league/${leagueID}/winners_bracket.json`
        : `https://api.sleeper.app/v1/league/${leagueID}/winners_bracket`;

    const [nflStateRes, leagueDataRes, playoffsRes] = await waitForAll(
        fetch(`https://api.sleeper.app/v1/state/nfl`, {compress: true}),
        fetch(leagueUrl, {compress: true}),
        fetch(bracketUrl, {compress: true}),
    )
    
    const [nflState, leagueData, playoffs] = await waitForAll(
        nflStateRes.json(),
        leagueDataRes.json(),
        playoffsRes.json(),
    )

	let year = nflState.league_season;
    // playoff_week_start can be 0 (commissioner has not set a playoff start
    // week) and /winners_bracket then returns null, which made `playoffs.pop()`
    // throw and killed this endpoint. Both values only decide HOW MANY weeks of
    // projections to fetch, so a long fallback is harmless; a short one would
    // silently miss late weeks.
    const regularSeasonLength = (leagueData.settings.playoff_week_start || 15) - 1;
    const playoffLength = (Array.isArray(playoffs) && playoffs.length)
        ? playoffs.pop().r
        : 3;
    const fullSeasonLength = regularSeasonLength + playoffLength;

    const resPromises = [
        fetch(`https://api.sleeper.app/v1/players/nfl`, {compress: true})
    ];

    for(let week = 1; week <= fullSeasonLength + 3; week++) {
        resPromises.push(
            fetch(`https://api.sleeper.app/projections/nfl/${year}/${week}?season_type=regular&position[]=DB&position[]=DEF&position[]=DL&position[]=FLEX&position[]=IDP_FLEX&position[]=K&position[]=LB&position[]=QB&position[]=RB&position[]=REC_FLEX&position[]=SUPER_FLEX&position[]=TE&position[]=WR&position[]=WRRB_FLEX&order_by=ppr`, {compress: true})
        );
    }
	
	const responses = await waitForAll(...resPromises);

    const resJSONs = [];
    for(const res of responses) {
        if(!res.ok) {
            throw error(500, "No luck");
        }
        resJSONs.push(res.json());
    }

    const weeklyData = await waitForAll(...resJSONs);

    const playerData = weeklyData.shift(); // first item is all player data, remaining items are weekly data for projections

    const scoringSettings = leagueData.scoring_settings;

    const computed = computePlayers(playerData, weeklyData, scoringSettings);

    // Shimmed leagues carry players Sleeper has never heard of (ESPN ids with no
    // espn_id match), keyed espn<id>. espn_shim records their name, position and
    // team in _meta.json; without this merge every one of them renders as
    // "Unknown player" in transactions, rosters and trades.
    if(shimmed) {
        try {
            const metaRes = await fetch(`${url.origin}/shim/v1/_meta.json`, {compress: true});
            if(metaRes.ok) {
                const meta = await metaRes.json();
                for(const [espnId, info] of Object.entries(meta.unmapped_players || {})) {
                    const key = `espn${espnId}`;
                    if(computed[key]) continue;
                    const name = (info && info.name) || "";
                    const sp = name.indexOf(" ");
                    computed[key] = {
                        fn: sp > 0 ? name.slice(0, sp) : name,
                        ln: sp > 0 ? name.slice(sp + 1) : "",
                        pos: (info && info.pos) || "",
                        t: (info && info.team) || undefined,
                    };
                }
            }
        } catch (e) {
            // A missing or malformed overlay must not take the endpoint down -
            // that is the failure this whole file already had once.
            console.error("shim player overlay skipped:", e);
        }
    }

    return json(computed);
}

const computePlayers = (playerData, weeklyData, scoringSettings) => {
    const computedPlayers = {};

    // create non weekly dependent player info
    for(const id in playerData) {
        const projPlayer = playerData[id];
        const player = {
            // injury_notes: projPlayer.injury_notes,
            fn: projPlayer.first_name,
            ln: projPlayer.last_name,
            pos: projPlayer.position,
        };
        if(projPlayer.team) {
            player.t = projPlayer.team;
            player.wi = {};
        }
        if(projPlayer.team && projPlayer.injury_status) {
            player.is = projPlayer.injury_status;
        }

        computedPlayers[id] = player;
    }

    // add weekly projections
    for(let week = 1; week <= weeklyData.length; week++) {
        for(const player of weeklyData[week - 1]) {
            const id = player.player_id;
            
            // check if the player is active in the NFL
            if(computedPlayers[id] == null || !computedPlayers[id].wi) continue;

            computedPlayers[id].wi[week] = {
                p: calculateProjection(player.stats, scoringSettings),
                o: player.opponent
            }
        }
    }

    computedPlayers["OAK"] = computedPlayers["LV"];
    return computedPlayers;
}

const calculateProjection = (projectedStats, scoreSettings) => {
    let score = 0
    for(const stat in projectedStats) {
        const multiplier = scoreSettings[stat] ? scoreSettings[stat] : 0;
        score += projectedStats[stat] * multiplier;
    }
    return round(score);
}