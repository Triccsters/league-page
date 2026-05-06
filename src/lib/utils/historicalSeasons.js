/**
 * historicalSeasons.js — manually-curated league history from before the
 * Sleeper era (Yahoo seasons). The /all-time page merges these into the
 * Champions by Season table.
 *
 * Sources: Yahoo Fantasy "Standings → Playoffs" page per season + Record Book.
 * Add a new entry for each season and the page will pick it up on next deploy.
 *
 * `manager` should match the Sleeper display_name where possible so lifetime
 * W-L cross-platform aggregation works in a future iteration. For now the
 * Champions table is the primary use.
 */

export const historicalSeasons = [
    {
        season: '2020',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'Joey', team: 'Waller Walkers' },
        runner_up: { manager: 'T.J.', team: 'Kareem Punt' },
        third_place: { manager: 'LordPmp', team: 'Christian Mingle' },
        championship_score: { winner: 123.46, loser: 119.70 },
        notes: 'Waller Walkers def. Kareem Punt in the final.',
    },
    {
        season: '2019',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'LordPmp', team: 'Quadfather' },
        runner_up: { manager: 'T.J.', team: 'Kareem Punt' },
        third_place: { manager: 'Joey', team: 'Fresh Cakes' },
        championship_score: { winner: 147.76, loser: 119.12 },
        notes: 'Fresh Cakes finished regular season 12-1-0 but lost the semifinal to Kareem Punt.',
    },
    {
        season: '2018',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'Austin', team: 'Mean Machine' },
        runner_up: { manager: '—', team: 'Trust Issues' },
        third_place: { manager: '—', team: 'The Disappointments' },
        championship_score: { winner: 143.96, loser: 123.08 },
        notes: 'The Disappointments dominated regular season at 11-2-0 but Mean Machine won the title via the playoff bracket. T.J. finished 7th with Kareem Punt going 5-8-0.',
    },
    {
        season: '2017',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'LordPmp', team: 'Jaywatch' },
        runner_up: { manager: '—', team: 'The Replacements' },
        third_place: { manager: '—', team: 'Savage AF' },
        championship_score: { winner: 108.12, loser: 90.24 },
        notes: 'LordPmp\'s first title (later won again in 2019 as Quadfather). Jaywatch finished regular season 11-2-0. T.J. finished 12th with Mr. Brightside (3-10-0).',
    },
    {
        season: '2016',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'Austin', team: 'Cooking with Julian' },
        runner_up: { manager: '—', team: '$100 and done' },
        third_place: { manager: '—', team: 'InstaGraham' },
        championship_score: { winner: 129.76, loser: 111.58 },
        notes: 'Austin\'s first title (won again in 2018 as Mean Machine). $100 and done finished regular season 11-2-0 but lost the final. T.J. finished 11th with The Absolute Madman (5-8-0).',
    },
    {
        season: '2015',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'Scott', team: "Scott's Team" },
        runner_up: { manager: '—', team: "The James Starks's" },
        third_place: { manager: '—', team: 'Iowa super troopers' },
        championship_score: { winner: 64.70, loser: 60.08 },
        notes: "Lowest-scoring final in league history (64.70 – 60.08). Scott's Team won despite being the underdog. T.J. finished 10th with can I geta witteness (7-6-0).",
    },
    {
        season: '2014',
        platform: 'yahoo',
        league_name: 'FL Players',
        champion: { manager: 'Colt', team: 'The Patriot Act' },
        runner_up: { manager: 'T.J.', team: "T.J.R's Team" },
        third_place: { manager: '—', team: 'White Lighting' },
        championship_score: { winner: 107.68, loser: 90.12 },
        notes: "T.J.'s first championship appearance — lost the final to Colt's The Patriot Act. Patriot Act dominated regular season at 10-3-0.",
    },
    {
        season: '2013',
        platform: 'yahoo',
        league_name: 'FL players',
        champion: { manager: 'Brett', team: 'Poppa pump' },
        runner_up: { manager: '—', team: 'CJ SPILLERS' },
        third_place: { manager: '—', team: 'J Rocks Dawgs' },
        championship_score: { winner: 107.44, loser: 70.84 },
        notes: "Cinderella run — Poppa pump entered the playoffs as the 6 seed (7-6-0) and beat the 2 seed CJ SPILLERS in a 36-point blowout final. T.J. finished 4th with Aaron Hernancuffs (9-4-0). League standings included a team literally named '2012 champ' (5th place).",
    },
    {
        season: '2012',
        platform: 'yahoo',
        league_name: 'FL players',
        champion: { manager: 'Austin', team: 'One dimension' },
        runner_up: { manager: '—', team: 'R. Corn on the Cobbs' },
        third_place: { manager: '—', team: 'Pappas Crew' },
        championship_score: { winner: 107, loser: 88 },
        notes: "Austin's first title (would go on to also win 2016 and 2018, becoming the league's most-decorated manager). One dimension entered playoffs as the 1 seed at 10-3-0 and never trailed. T.J. finished 11th with TJ Rizzle Fresh (5-7-1). The team named '2012 champ' actually existed in 2012 standings — went 7-6-0 and lost in QF, ironically.",
    },
    // Add more years above this line — copy the structure above.
    // Yahoo seasons to backfill: 2009–2011.
];
