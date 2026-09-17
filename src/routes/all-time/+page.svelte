<script>
    import CombinedStandings from '$lib/Records/CombinedStandings.svelte';
    import { site } from '$lib/utils/flpHistory';
</script>

<svelte:head><title>All-Time Stats | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>All-Time Stats</h1>
    <CombinedStandings />
    <p class="more">Single-game and season records are in the <a href="/record-book">Record Book</a>. Head-to-head history is in <a href="/rivalries">Rivalries</a>.</p>
</div>

<style>
    .holder { max-width: 1100px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; }
    .more { text-align: center; margin: 2em 0 1em; opacity: 0.8; }
    .more a { color: #3498db; }
</style>
