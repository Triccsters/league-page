<script>
	import { Standings } from '$lib/components'
	import MedianStandings from '$lib/Standings/MedianStandings.svelte';

	export let data;
	const {standingsData, leagueTeamManagersData} = data;
</script>

<style>
	.holder {
		position: relative;
		z-index: 1;
		text-align: center;
	}
</style>

<div class="holder">
	<Standings {standingsData} {leagueTeamManagersData} />
	<MedianStandings />
</div>
