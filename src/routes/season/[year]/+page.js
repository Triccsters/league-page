import { site } from '$lib/utils/flpHistory';

// The yearbook for one season. The page fetches static/data/seasons.json itself;
// this resolves the year and writes the text a shared link shows in a group chat.
export function load({ params }) {
    const year = parseInt(params.year, 10);
    return {
        year,
        og: {
            title: `${year} in ${site.league_name}`,
            description: `Final standings, every matchup, the playoff bracket, the draft, the trades and the season's awards.`,
        },
    };
}
