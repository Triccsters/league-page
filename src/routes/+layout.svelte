<!-- __layout.svelte -->
<script>
	import { Nav, Footer } from "$lib/components"
	import MyTeamBar from "$lib/MyTeam/MyTeamBar.svelte";
    import { dev } from '$app/environment';
    import { page } from '$app/stores';
    import { leagueName } from '$lib/utils/leagueInfo';
    // link previews: pages can set data.og = { title, description }
    $: og = $page.data?.og || {};
    $: ogTitle = og.title || leagueName;
    $: ogDesc = og.description || `${leagueName} fantasy football: matchups, recaps, rivalries, records and playoff odds.`;
    import { injectAnalytics } from '@vercel/analytics/sveltekit';
 
    injectAnalytics({ mode: dev ? 'development' : 'production' });
</script>

<svelte:head>
    <meta name="description" content={ogDesc} />
    <meta property="og:site_name" content={leagueName} />
    <meta property="og:type" content="website" />
    <meta property="og:title" content={ogTitle} />
    <meta property="og:description" content={ogDesc} />
    <meta property="og:url" content={$page.url.href} />
    <meta property="og:image" content={`${$page.url.origin}/favicons/android-chrome-512x512.png`} />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content={ogTitle} />
    <meta name="twitter:description" content={ogDesc} />
</svelte:head>

<main>
    <Nav /> <!-- adds the nav (small and large) -->
    <MyTeamBar />
  
    <slot />

    <Footer /> <!-- adds the footer -->
</main>