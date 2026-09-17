<script>
    import { recaps } from '$lib/utils/recaps';
    import { nameOf } from '$lib/utils/flpHistory';
</script>

<svelte:head><title>Weekly Recaps | FL Players</title></svelte:head>

<div class="holder">
    <h1>Weekly Recaps</h1>
    <p class="sub">Every week: results, the closest game, the biggest bench mistake, and a timeline of how each matchup played out.</p>

    <div class="links">
        <a href="/timeline">Live matchup timeline →</a>
        <a href="/rivalries">All-time rivalries →</a>
    </div>

    {#if recaps.length === 0}
        <p class="sub">No recaps yet. The first one appears after week 1 is final.</p>
    {/if}
    {#each recaps as r}
        {@const f = r.facts}
        <a class="post" href="/recaps/{r.slug}">
            <div class="head">
                <h2>{r.season} · {r.title}</h2>
                {#if r.video}<span class="tag">▶ Video</span>{/if}
            </div>
            {#if r.intro}<p>{r.intro.length > 240 ? r.intro.slice(0, 240) + '…' : r.intro}</p>{/if}
            <ul>
                {#if f.closest}<li>Closest: {nameOf(f.closest.winner.manager)} over {nameOf(f.closest.loser.manager)} by {f.closest.margin}</li>{/if}
                {#if f.high}<li>High score: {nameOf(f.high.manager)}, {f.high.points}</li>{/if}
                {#if f.bench_regret}<li>Most left on the bench: {nameOf(f.bench_regret.manager)}, {f.bench_regret.points}</li>{/if}
            </ul>
        </a>
    {/each}
</div>

<style>
    .holder { max-width: 820px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub { text-align: center; opacity: 0.75; }
    .links { display: flex; justify-content: center; gap: 1.5em; margin: 1em 0 1.5em; flex-wrap: wrap; }
    .links a { color: #3498db; }
    .post { display: block; color: inherit; text-decoration: none; border: 1px solid rgba(127,127,127,0.35); border-radius: 8px; padding: 1em 1.2em; margin-bottom: 1em; }
    .post:hover { border-color: #3498db; }
    .head { display: flex; justify-content: space-between; align-items: center; gap: 1em; }
    h2 { margin: 0; font-size: 1.2em; }
    .tag { background: #c0392b; color: #fff; border-radius: 4px; padding: 0.15em 0.5em; font-size: 0.8em; white-space: nowrap; }
    ul { margin: 0.5em 0 0; padding-left: 1.2em; }
</style>
