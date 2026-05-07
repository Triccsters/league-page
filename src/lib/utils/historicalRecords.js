/**
 * historicalRecords.js — Yahoo-era league records book.
 *
 * Format per record: { stat, holder, opponent?, value, season, week? }
 *   - holder is the team that achieved the record
 *   - opponent (when relevant) is the other team in that matchup
 *   - season "—" means unknown / current-season at time of screenshot
 *
 * Combined with computed Sleeper records on the /record-book page.
 */

export const historicalRecords = {
    head_to_head: [
        { stat: 'Most career wins', holder: 'Kareem Punt', value: 12, season: '—' },
        { stat: 'Most wins (single season)', holder: 'Fresh Cakes', value: 13, season: '2019' },
        { stat: 'Longest career win streak', holder: 'Kareem Punt', value: 7, season: '—' },
        { stat: 'Longest win streak (single season)', holder: 'Fresh Cakes', value: 11, season: '2019' },
        { stat: 'Current win streak', holder: 'Waller Walkers', value: 3, season: '2020' },
        { stat: 'Most career losses', holder: 'What The Buck / Fuck chowbox', value: 11, season: '—' },
        { stat: 'Most losses (single season)', holder: 'The Chowbox', value: 13, season: '2018' },
        { stat: 'Longest losing streak (single season)', holder: "Scott's Team", value: 10, season: '2016' },
        { stat: 'Current losing streak', holder: 'The Chowbox', value: 7, season: '2020' },
    ],
    margin_of_victory: [
        { stat: 'Largest single-week blowout', holder: "Hurst Don't It", opponent: 'What The Buck', value: 103.02, season: '—', week: 3 },
        { stat: 'Largest single-week blowout (all-time)', holder: 'Quadfather', opponent: 'Ramen noodles', value: 125.42, season: '2019', week: 5 },
        { stat: 'Smallest single-week win', holder: 'Kareem Punt', opponent: 'Fuck chowbox', value: 0.60, season: '—', week: 13 },
        { stat: 'Smallest single-week win (all-time)', holder: 'My Time Is Now!', opponent: 'can I geta witteness', value: 0.04, season: '2015', week: 16 },
        { stat: 'Highest avg margin of victory (season)', holder: "Blazing Cow's", value: 43.21, season: '—' },
        { stat: 'Highest avg margin of victory (all-time)', holder: 'Baby Got Dak', value: 54.45, season: '2019' },
        { stat: 'Largest avg margin of defeat (season)', holder: 'What The Buck', value: 36.85, season: '—' },
        { stat: 'Largest avg margin of defeat (all-time)', holder: 'Kareem Punt', value: 48.55, season: '2019' },
    ],
    team_points: [
        { stat: 'Most points (single week)', holder: "Hurst Don't It", opponent: 'What The Buck', value: 165.86, season: '—', week: 3 },
        { stat: 'Most points (single week, all-time)', holder: 'Quadfather', opponent: 'What The Buck', value: 224.66, season: '2019', week: 3 },
        { stat: 'Most points (single season, all-time)', holder: 'Waller Walkers', value: 1944.86, season: '2020' },
        { stat: 'Highest season avg', holder: 'Move Bullocks', value: 121.55, season: '2018' },
        { stat: 'Fewest points (single week)', holder: 'Not Blankenships', opponent: "Blazing Cow's", value: 31.42, season: '—', week: 10 },
        { stat: 'Fewest points (single week, all-time)', holder: 'Steel Hard Dawg', value: 8.6, season: '2018', week: 1 },
        { stat: 'Fewest points (single season, all-time)', holder: 'NotLast', value: 80, season: '2020' },
        { stat: "Fewest points (season avg, all-time)", holder: 'The Chowbox', value: 86.62, season: '2018' },
    ],
    offensive_points: [
        { stat: 'Most offensive points (single week)', holder: "Hurst Don't It", opponent: 'What The Buck', value: 154, season: '—', week: 3 },
        { stat: 'Most offensive points (single week, all-time)', holder: 'Quadfather', opponent: 'What The Buck', value: 208.06, season: '2019', week: 3 },
        { stat: 'Most offensive points (season, all-time)', holder: 'Waller Walkers', value: 1827.96, season: '2020' },
        { stat: 'Fewest offensive points (single week)', holder: 'Waller Walkers', opponent: 'Dead Dawgs', value: 47.78, season: '—', week: 4 },
        { stat: 'Fewest offensive points (single week, all-time)', holder: 'East Power', opponent: 'Dead Dawgs', value: 39.36, season: '2018', week: 11 },
    ],
    defensive_points: [
        { stat: 'Most defensive points (single week)', holder: "Hurst Don't It", opponent: 'Christian Mingle', value: 27, season: '—', week: 7 },
        { stat: 'Most defensive points (single week, all-time)', holder: 'Not Blankenships', opponent: 'Christian Mingle', value: 49, season: '2018', week: 7 },
        { stat: 'Fewest defensive points (single week)', holder: 'Lex chowbox', opponent: 'Christian Mingle', value: -7, season: '—', week: 1 },
    ],
    kicking_points: [
        { stat: 'Most kicking points (single week)', holder: "Hurst Don't It", value: 19, season: '—', week: 11 },
        { stat: 'Most kicking points (season, all-time)', holder: 'Cooking with Lulus', value: 165, season: '2018' },
        { stat: 'Fewest kicking points (single week)', holder: 'The Chowbox', opponent: 'Christian Mingle', value: 0, season: '—', week: 11 },
    ],
    touchdowns: [
        { stat: 'Most TDs (single week, all-time)', holder: 'What The Buck', value: 17, season: '—', week: 3 },
        { stat: 'Most TDs (single season, all-time)', holder: "Hurst Don't It", value: 199, season: '2020' },
    ],
    yardage: [
        { stat: 'Most passing yards (single week)', holder: "We Ain't Dem Boys", opponent: 'Christian Mingle', value: 532, season: '—', week: 4 },
        { stat: 'Most passing yards (season, all-time)', holder: "Hurst Don't It", value: 4046, season: '2018' },
        { stat: 'Most rushing yards (single week, all-time)', holder: 'Quadfather', opponent: 'Ramen noodles', value: 460, season: '2019', week: 5 },
        { stat: 'Most rushing yards (season, all-time)', holder: 'Jaywatch', value: 4564, season: '2017' },
        { stat: 'Most receiving yards (single week, all-time)', holder: 'Quadfather', opponent: 'Ramen noodles', value: 478, season: '2019', week: 5 },
        { stat: 'Most receiving yards (season, all-time)', holder: 'Kareem Punt', value: 5662, season: '2019' },
    ],
    strength_of_schedule: [
        { stat: 'Hardest weekly avg (current)', holder: 'What The Buck', value: 115.42, season: '—' },
        { stat: 'Hardest weekly avg (all-time)', holder: 'Ramen noodles', value: 119.49, season: '2019' },
        { stat: 'Easiest weekly avg (current)', holder: 'The Chowbox', value: 98.56, season: '—' },
        { stat: 'Easiest weekly avg (all-time)', holder: 'Jaywatch', value: 81.38, season: '2017' },
    ],
};
