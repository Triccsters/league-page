<script>
    import { leagueName } from '$lib/utils/leagueInfo';
    import Trackers from '$lib/Charts/Trackers.svelte';
</script>

<svelte:head><title>League Trackers | {leagueName}</title></svelte:head>

<Trackers />
