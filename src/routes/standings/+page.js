import { getLeagueStandings, getLeagueTeamManagers } from '$lib/utils/helper';
import { getAllPlayStandings, getLineupEfficiency } from '$lib/utils/helperFunctions/leagueAllPlay';

// one Standings page: the all-play and lineup efficiency sections need their data here too
export async function load() {

    const standingsData = getLeagueStandings();
    const leagueTeamManagersData = getLeagueTeamManagers();
    const allPlayData = getAllPlayStandings();
    const efficiencyData = getLineupEfficiency();

    return {
        standingsData,
        leagueTeamManagersData,
        allPlayData,
        efficiencyData,
    };
}
