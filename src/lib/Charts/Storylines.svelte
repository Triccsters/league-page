<script>
    // "This week's storylines" box for the Matchups page: rivalry, revenge and streak flags.
    import previews from '$lib/data/previews.json';
    import { nameOf, slugFor, fillNames } from '$lib/utils/flpHistory';
    const withFlags = previews.games.filter(g => g.flags.length);
</script>

{#if previews.week && withFlags.length}
    <details class="story" open>
        <summary>🔥 Week {previews.week} storylines</summary>
        <ul>
            {#each withFlags as g}
                <li><a href="/rivalries/{slugFor(g.a, g.b)}"><b>{nameOf(g.a)} vs {nameOf(g.b)}</b></a>: {g.flags.map(fillNames).join(' · ')}</li>
            {/each}
        </ul>
        <a class="more" href="/preview">Full week {previews.week} preview with win chances →</a>
    </details>
{/if}

<style>
    .story { max-width: 900px; margin: 1em auto 0; padding: 0.6em 1em; border: 1px solid rgba(231, 76, 60, 0.45); border-radius: 8px; font-size: 0.92em; position: relative; z-index: 2; }
    summary { cursor: pointer; font-weight: 700; }
    ul { margin: 0.4em 0; padding-left: 1.1em; }
    li { margin: 0.2em 0; }
    a { color: inherit; }
    .more { color: #3498db; font-size: 0.9em; }
</style>
