import unclaimed from '$lib/data/unclaimed.json';

// One route, two views, the same shape as /manager?manager=<id>: the index with no
// query, one team with ?team=<slug>. unclaimed.json is built by build_unclaimed() in
// scripts/update_site.py from the handles history.json marks hidden.
export async function load({ url }) {
    const slug = url?.searchParams?.get('team');

    // champions first, then the teams that reached a final, then the most games played:
    // the ones most likely to be remembered are the ones worth putting first
    const teams = [...unclaimed].sort((a, b) =>
        (b.titles.length - a.titles.length)
        || (b.finalsLost.length - a.finalsLost.length)
        || (b.gamesPlayed - a.gamesPlayed)
        || a.name.localeCompare(b.name));

    const index = slug ? teams.findIndex(t => t.slug === slug) : -1;

    return {
        teams,
        slug: slug || null,
        team: index > -1 ? teams[index] : null,
        prev: index > 0 ? teams[index - 1] : null,
        next: index > -1 && index < teams.length - 1 ? teams[index + 1] : null,
    };
}
