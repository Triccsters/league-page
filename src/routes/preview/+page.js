import previews from '$lib/data/previews.json';
import { nameOf, site, fillNames } from '$lib/utils/flpHistory';

export function load() {
    const lines = previews.games.slice(0, 3).map(g => `${nameOf(g.a)} vs ${nameOf(g.b)}${g.flags[0] ? ': ' + fillNames(g.flags[0]) : ''}`);
    return {
        og: {
            title: previews.week ? `${site.league_name} week ${previews.week} preview` : `${site.league_name} preview`,
            description: lines.join(' · ') || 'Win chances, head-to-head history and storylines for every game.',
        },
    };
}
