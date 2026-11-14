<script>
    // A Spotify show player on the home page (T.J., 2026-11-13). A league turns it on with
    //   export const spotifyShow = '<show id>';   and optionally   export const podcastTitle = '...';
    // in its own leagueInfo.js. The id is the part after /show/ in the show's Spotify link.
    import * as leagueInfo from '$lib/utils/leagueInfo';
    const id = leagueInfo.spotifyShow;
    const title = leagueInfo.podcastTitle || 'The podcast';
</script>

{#if id}
    <section class="pod">
        <h3>{title}</h3>
        <iframe title={title} src="https://open.spotify.com/embed/show/{id}?utm_source=generator&theme=0" width="100%" height="232" frameborder="0" loading="lazy"
            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe>
    </section>
{/if}

<style>
    .pod { max-width: 1000px; margin: 1em auto; padding: 0 1em; }
    h3 { margin: 0 0 0.5em; }
    iframe { border-radius: 12px; }
</style>
