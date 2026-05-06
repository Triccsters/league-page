import { getAllTimeStats } from '$lib/utils/helperFunctions/leagueAllTime';

export async function load() {
    const allTimeData = getAllTimeStats();
    return { allTimeData };
}
