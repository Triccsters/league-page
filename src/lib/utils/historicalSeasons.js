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
    // Add more years above this line — copy the structure above.
    // Yahoo seasons to backfill: 2009–2018.
];
