import { getLineupEfficiency } from '$lib/utils/helperFunctions/leagueAllPlay';

export async function load() {
    const efficiencyData = getLineupEfficiency();
    return { efficiencyData };
}
