import { getAllPlayStandings } from '$lib/utils/helperFunctions/leagueAllPlay';

export async function load() {
    const allPlayData = getAllPlayStandings();
    return { allPlayData };
}
