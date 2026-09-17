<!-- __layout.svelte -->
<script>
	import { Nav, Footer } from "$lib/components"
	import MyTeamBar from "$lib/MyTeam/MyTeamBar.svelte";
    import { dev } from '$app/environment';
    import { injectAnalytics } from '@vercel/analytics/sveltekit';
 
    injectAnalytics({ mode: dev ? 'development' : 'production' });
</script>

<main>
    <Nav /> <!-- adds the nav (small and large) -->
    <MyTeamBar />
  
    <slot />

    <Footer /> <!-- adds the footer -->
</main>