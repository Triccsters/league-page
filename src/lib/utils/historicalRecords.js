/**
 * historicalRecords.js — League records book transcribed from Yahoo's
 * Record Book screenshots (covers seasons 2010, 2012-2020, omits 2011).
 *
 * Used by /records and the All-Time Records section of /all-time.
 */

export const historicalRecords = {
    head_to_head: [
        { stat: 'Most wins (single season)', holder: 'Fresh Cakes', value: 13, season: '2019' },
        { stat: 'Longest win streak', holder: 'Fresh Cakes', value: 11, season: '2019' },
        { stat: 'Most losses (single season)', holder: 'The Chowbox', value: 13, season: '2018' },
        { stat: 'Longest losing streak', holder: "Scott's Team", value: 10, season: '2016' },
    ],
    margin_of_victory: [
        { stat: 'Largest single-week blowout', holder: 'Quarterfinal vs Ramen noodles', value: 125.42, season: '2019', week: 5 },
        { stat: 'Smallest single-week win', holder: 'My Time Is Now vs can I geta witteness', value: 0.04, season: '2015', week: 16 },
        { stat: 'Highest avg margin of victory (season)', holder: 'Baby Got Dak', value: 54.45, season: '2019' },
        { stat: 'Highest avg margin of defeat (season)', holder: 'Kareem Punt', value: 48.55, season: '2019' },
    ],
    team_points: [
        { stat: 'Most points in a single week', holder: 'Quarterfinal vs What The Buck', value: 224.66, season: '2019', week: 3 },
        { stat: 'Fewest points in a single week', holder: 'Steel Hard Dawg', value: 8.6, season: '2018', week: 1 },
        { stat: 'Most points in a season', holder: 'Walker Walkers', value: 1944.86, season: 'all-time' },
        { stat: 'Fewest points in a season', holder: 'NotLast', value: 80, season: '2020' },
    ],
    offensive_points: [
        { stat: 'Most offensive points (single week)', holder: 'Quarterfinal vs What The Buck', value: 208.06, season: '2019', week: 3 },
        { stat: 'Fewest offensive points (single week)', holder: 'East Power vs Dead Dawgs', value: 39.36, season: '2018', week: 11 },
    ],
    defensive_points: [
        { stat: 'Most defensive points (single week)', holder: 'Hurst Don\'t It vs Dead Sleepers', value: 49, season: '2018', week: 3 },
    ],
    kicking_points: [
        { stat: 'Most kicking points (single season)', holder: 'Cooking with Lulus', value: 165, season: '2018' },
    ],
    touchdowns: [
        { stat: 'Most TDs (single week)', holder: 'What The Buck', value: 17, season: '—', week: 3 },
        { stat: 'Most TDs (single season)', holder: "I Fart Dutch RUDDER", value: 18, season: '2019' },
        { stat: 'Most TDs (season all-time)', holder: 'The Disappointments', value: 199, season: '2018' },
    ],
    yardage: [
        { stat: 'Most passing yards (single week)', holder: "We Ain't Dem Boys vs Christian Mingle", value: 532, season: '—', week: 4 },
        { stat: 'Most passing yards (season all-time)', holder: "Hurst Don't It", value: 4046, season: '2018' },
        { stat: 'Most rushing yards (single week)', holder: "Quarterfinal vs Ramen noodles", value: 460, season: '2019', week: 5 },
        { stat: 'Most rushing yards (season all-time)', holder: 'Jaywatch', value: 4564, season: '2017' },
        { stat: 'Most receiving yards (single week)', holder: 'Quarterfinal vs Ramen-noodles', value: 478, season: '2019', week: 5 },
        { stat: 'Most receiving yards (season all-time)', holder: 'Kareem Punt', value: 5662, season: '2019' },
    ],
    strength_of_schedule: [
        { stat: 'Hardest weekly schedule average', holder: 'Ramen noodles', value: 119.49, season: '2019' },
        { stat: 'Easiest weekly schedule average', holder: 'Jaywatch', value: 81.38, season: '2017' },
    ],
};
