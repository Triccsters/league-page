import { recapBySlug } from '$lib/utils/recaps';
import { nameOf, site } from '$lib/utils/flpHistory';

export function load({ params }) {
    const r = recapBySlug(params.slug);
    let og = null;
    if (r) {
        const f = r.facts || {};
        const bits = [];
        if (f.high) bits.push(`High score: ${nameOf(f.high.manager)} ${f.high.points}`);
        if (f.closest) bits.push(`Closest: ${nameOf(f.closest.winner.manager)} by ${f.closest.margin}`);
        if (f.blowout) bits.push(`Blowout: ${nameOf(f.blowout.winner.manager)} by ${f.blowout.margin}`);
        og = {
            title: `${site.league_name} ${r.season}: ${r.title}`,
            description: (r.intro ? r.intro.slice(0, 160) : bits.join(' · ')) || 'Weekly recap',
        };
    }
    return { slug: params.slug, og };
}
