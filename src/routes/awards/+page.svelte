<script>
	import { Awards } from '$lib/components'
	import { waitForAll } from '$lib/utils/helper';
	import LinearProgress from '@smui/linear-progress';
	import Overview from '$lib/Charts/Overview.svelte';
	import overviews from '$lib/data/overviews_extra.json';
	// one Trophy Room (T.J., 2026-11-15): the awards page that was /hall-of-fame, then the seasons
	import TrophyCase from '../hall-of-fame/+page.svelte';

    export let data;
    const {awardsData, teamManagersData} = data;
</script>

<style>
    .awards {
        display: block;
        margin: 30px auto;
		width: 95%;
		max-width: 1000px;
		position: relative;
		z-index: 1;
		overflow-y: hidden;
    }

	.loading {
		display: block;
		width: 85%;
		max-width: 500px;
		margin: 80px auto;
	}

	.byseason {
		text-align: center;
		margin: 0.5em 0 0;
	}

	.nothingYet {
		display: block;
		width: 85%;
		max-width: 500px;
		margin: 80px auto;
		text-align: center;
	}

	.yearbookLink {
		text-align: center;
		margin: -0.2em 0 1.2em;
		font-size: 0.9em;
	}
	.yearbookLink.top { margin-top: 0.4em; }
	.yearbookLink a { color: #3498db; font-weight: 700; text-decoration: none; }
	.yearbookLink a:hover { text-decoration: underline; }
</style>

<TrophyCase />

<div class="awards">
	<h2 class="byseason">Season by season</h2>
	<p class="yearbookLink top"><a href="/season">Every season's full page →</a></p>
	{#await waitForAll(awardsData, teamManagersData) }
		<div class="loading">
			<p>Retrieving awards data...</p>
			<LinearProgress indeterminate />
		</div>
	{:then [podiums, leagueTeamManagers] }
		{#each podiums as podium}
			<Overview text={overviews.seasons?.[podium.year]} heading="{podium.year} in review" />
			<p class="yearbookLink"><a href="/season/{podium.year}">The whole {podium.year} season →</a></p>
			<Awards {podium} {leagueTeamManagers} />
		{:else}
			<p class="nothingYet">No seasons have been completed yet, so no awards have been earned...</p>
		{/each}
		{#each Object.keys(overviews.seasons || {}).filter(y => !podiums.some(p => String(p.year) === y)).sort((a, b) => b - a) as year}
			<Overview text={overviews.seasons[year]} heading="{year} in review" />
			<p class="yearbookLink"><a href="/season/{year}">The whole {year} season →</a></p>
		{/each}
	{:catch error}
		<!-- promise was rejected -->
		<p>Something went wrong: {error.message}</p>
	{/await}
</div>