<script>
    import { leagueName } from '$lib/utils/helper';
    import ManagerRow from './ManagerRow.svelte'
    import unclaimed from '$lib/data/unclaimed.json';

    export let managers, leagueTeamManagers;

    let innerWidth;
</script>

<svelte:window bind:innerWidth={innerWidth} />

<style>
    .managerContainer {
        width: 100%;
        margin: 2em 0 5em;
    }

    .managerConstrained {
        width: 97%;
        max-width: 800px;
        margin: 0 auto;
    }

    h2 {
        text-align: center;
        font-size: 2.8em;
        margin: 2em 0 1.5em;
        line-height: 1em;
    }

    .unclaimedLink {
        display: block;
        margin: 1.5em 0 0;
        padding: 1em 1.5em;
        border: 1px dashed var(--ccc);
        border-radius: 2em;
        background-color: var(--fff);
        color: var(--g555);
        font-weight: 700;
        text-align: center;
        text-decoration: none;
    }

    .unclaimedLink:hover {
        box-shadow: 0 0 10px 0 var(--bbb);
    }

    .unclaimedLink .sub {
        display: block;
        font-weight: 300;
        font-style: italic;
        font-size: 0.85em;
        margin-top: 0.2em;
    }

    @media (max-width: 520px) {
        h2 {
            text-align: center;
            font-size: 2em;
            margin: 1.5em 0 1em;
            line-height: 1em;
        }
    }
</style>

<div class="managerContainer">
    <h2>{leagueName} Managers</h2>
    <div class="managerConstrained">
        {#each managers as manager, key}
            <ManagerRow {manager} {leagueTeamManagers} {key} />
        {/each}

        <!-- the team-seasons from the Yahoo years with no manager attached to them -->
        {#if unclaimed.length}
            <a class="unclaimedLink" href="/unclaimed">
                {unclaimed.length} teams we never identified &rarr;
                <span class="sub">Recognise one? It might be yours.</span>
            </a>
        {/if}
    </div>

</div>