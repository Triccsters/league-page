<script>
	import { getAvatarFromTeamManagers, getTeamNameFromTeamManagers, renderManagerNames } from "$lib/utils/helperFunctions/universalFunctions";

    export let leagueTeamManagers, managerID = null, rosterID = null, year, compressed = false, points = null;

    // Former managers: nobody on this team is on a roster this season.
    const tmm = leagueTeamManagers.teamManagersMap || {};
    const cur = leagueTeamManagers.currentSeason;
    const currentIDs = new Set(Object.values(tmm[cur] || {}).flatMap(t => t.managers || []));
    const lastYearFor = (id) => Math.max(0, ...Object.entries(tmm)
        .filter(([, teams]) => Object.values(teams).some(t => (t.managers || []).includes(id))).map(([y]) => +y));
    $: ids = managerID ? [managerID] : rosterID ? (tmm[!year || year > cur ? cur : year]?.[rosterID]?.managers || []) : [];
    $: former = currentIDs.size > 0 && ids.length > 0 && !ids.some(id => currentIDs.has(id));
    $: leftIn = former ? Math.max(...ids.map(lastYearFor)) + 1 : null;

    let user = null;

    if(managerID) {
        user = leagueTeamManagers.users[managerID];
    }
</script>

<style>
    .leftTag { display: inline-block; font-size: 0.66em; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;
        background: #5d6d7e; color: #fff; border-radius: 3px; padding: 0.05em 0.4em; margin: 0.1em 0; white-space: nowrap; }
	.teamAvatar {
		vertical-align: middle;
		border-radius: 50%;
		height: 40px;
		margin-right: 15px;
		border: 0.25px solid #777;
	}

    .recordTeam {
        display: flex;
    }

    .name {
        margin: auto 0;
    }

    .managerNames {
        font-size: 0.75em;
        font-style: italic;
        color: var(--g999);
        max-width: 180px;
        white-space: normal;
        text-align: left;
    }

    .compressed {
		height: 30px;
		margin-right: 6px;
    }

    @media (max-width: 405px) {
        .teamAvatar {
            height: 25px;
            margin-right: 8px;
        }

        .compressed {
            height: 20px;
            margin-right: 4px;
        }
    }

    @media (max-width: 295px) {
        .teamAvatar {
            display: none;
        }
    }

</style>

<div class="recordTeam">
    {#if user}
        <img alt="team avatar" class="teamAvatar{compressed ? " compressed" : ""}" src="{`https://sleepercdn.com/avatars/thumbs/${user.avatar}`}" />
    {:else if rosterID}
        <img alt="team avatar" class="teamAvatar{compressed ? " compressed" : ""}" src="{getAvatarFromTeamManagers(leagueTeamManagers, rosterID, year)}" />
    {/if}
    <span class="name">
        <div class="teamName">
            {#if user}
                {user.display_name}
            {:else if rosterID}
                {getTeamNameFromTeamManagers(leagueTeamManagers, rosterID, year)}
                {points ? ` (${points})` : ""}
            {/if}
        </div>
        {#if former}
            <div class="leftTag">Left league in {leftIn}</div>
        {/if}
        {#if !user}
            <div class="managerNames">
                {renderManagerNames(leagueTeamManagers, rosterID, year)}
            </div>
        {/if}
    </span>
</div>