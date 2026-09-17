import odds from '$lib/data/odds.json';
import { nameOf, site } from '$lib/utils/flpHistory';

export function load() {
    const top = odds.teams.slice(0, 3).map(t => `${nameOf(t.h)} ${t.playoff}%`).join(', ');
    return {
        og: {
            title: `${site.league_name} playoff odds after week ${odds.through_week}`,
            description: `Chance to make the playoffs: ${top}. Based on ${odds.sims.toLocaleString()} simulated seasons.`,
        },
    };
}
