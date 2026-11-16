import {
    waitForAll,
    getLeagueRosters,
    getLeagueTeamManagers,
    getLeagueData,
    getLeagueTransactions,
    getAwards,
    getLeagueRecords,
    managers as managersObj,
    resolveManagerParam
} from '$lib/utils/helper';
export async function load({ url }) {
    if(!managersObj.length) return false;
    const managersInfo = waitForAll(
        getLeagueRosters(),    
        getLeagueTeamManagers(),
        getLeagueData(),
        getLeagueTransactions(),
        getAwards(),
        getLeagueRecords(),
    );

    const manager = url?.searchParams?.get('manager');

    const props = {
        manager: resolveManagerParam(manager),
        managers: managersObj,
        managersInfo
    }

    return props;
}