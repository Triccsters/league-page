import { rivalry, nameOf, pairFromSlug, site } from '$lib/utils/flpHistory';

// Data for the page plus the text a shared link shows in a group chat
export function load({ params }) {
    const [x, y] = pairFromSlug(params.slug);
    const r = rivalry(x, y);
    const X = nameOf(x), Y = nameOf(y);
    const lead = r.all.x === r.all.y ? `tied ${r.all.x}-${r.all.y}` : r.all.x > r.all.y ? `${X} leads ${r.all.x}-${r.all.y}` : `${Y} leads ${r.all.y}-${r.all.x}`;
    const streak = r.streak && r.streak.n >= 2 ? ` ${nameOf(r.streak.who)} has won ${r.streak.n} straight.` : '';
    return {
        slug: params.slug,
        og: {
            title: `${X} vs ${Y}: ${lead}`,
            description: `${r.meetings.length} meetings in ${site.league_name} since ${r.meetings[0]?.season ?? site.first_season}.${streak}`,
        },
    };
}
