<script>
	import { Standings } from '$lib/components'
	import MedianStandings from '$lib/Standings/MedianStandings.svelte';
	import PowerBoard from '$lib/Charts/PowerBoard.svelte';
	import PowerLines from '$lib/Charts/PowerLines.svelte';
	// the other standings-type pages, folded in as sections (T.J., 2026-11-13)
	import AllPlay from '../all-play/+page.svelte';
	import Luck from '../luck/+page.svelte';
	import Efficiency from '../efficiency/+page.svelte';

	export let data;
	const {standingsData, leagueTeamManagersData} = data;
</script>

<style>
	.holder {
		position: relative;
		z-index: 1;
		text-align: center;
	}
	.fold { margin-top: 2.5em; border-top: 1px solid rgba(127,127,127,0.3); padding-top: 0.5em; }
	.fold > h2 { text-align: center; margin: 0.6em 0 0; }
	.fold > p { text-align: center; opacity: 0.7; font-size: 0.9em; margin: 0.2em 1em 0; }
	/* each folded page brings its own big title; the section heading above replaces it */
	.fold :global(h1) { display: none; }
</style>

<div class="holder">
	<Standings {standingsData} {leagueTeamManagersData} />
	<MedianStandings />
</div>

<section class="fold">
	<PowerBoard />
</section>

<section class="fold">
	<PowerLines />
</section>

<section class="fold">
	<h2>All-play standings</h2>
	<p>Your record if you played every other team every week. It takes the schedule out of it.</p>
	<AllPlay {data} />
</section>

<section class="fold">
	<h2>Luck</h2>
	<p>Actual wins against the wins your scores deserved.</p>
	<Luck />
</section>

<section class="fold">
	<h2>Lineup efficiency</h2>
	<p>Points scored against the best lineup you could have set.</p>
	<Efficiency {data} />
</section>
