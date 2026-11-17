<script>
    import { nameOf, site } from '$lib/utils/flpHistory';
    import all from '$lib/data/seasons.json';
    import unclaimed from '$lib/data/unclaimed.json';

    // newest first - people look up the recent ones more often
    const years = Object.keys(all.seasons).map(Number).sort((a, b) => b - a);
    const S = (y) => all.seasons[String(y)];
    const champs = {};
    for (const y of years) {
        const c = S(y).champion;
        if (c) champs[c] = (champs[c] || 0) + 1;
    }
    const titleCount = Object.keys(champs).length;
    const n1 = (x) => (x == null ? '' : (Math.round(x * 100) / 100).toLocaleString());
</script>

<svelte:head><title>Seasons | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>Every season</h1>
    <p class="note">
        {years.length} seasons on record, {Math.min(...years)} to {Math.max(...years)}.
        {#if site.missing_seasons?.length}
            The league played {site.missing_seasons.join(' and ')} without T.J., so no game data for
            those years is on his account. Both have since been part-reconstructed from the managers'
            own public Yahoo profiles &mdash;
            {#each site.missing_seasons as m, i}<a href="/season/{m}">{m}</a>{#if i < site.missing_seasons.length - 2}, {:else if i === site.missing_seasons.length - 2}&nbsp;and {/if}{/each}.
        {/if}
        {titleCount} different managers have won it.
    </p>

    <div class="grid">
        {#each years as y}
            {@const s = S(y)}
            {@const top = s.standings[0]}
            <a class="card" href="/season/{y}" class:live={s.current}>
                <div class="yr">{y}</div>
                {#if s.champion}
                    <div class="ch"><span>🏆</span>{nameOf(s.champion)}</div>
                    {#if s.title_game}
                        <small>beat {nameOf(s.runner_up)}
                            {n1(Math.max(s.title_game.pa, s.title_game.pb))}–{n1(Math.min(s.title_game.pa, s.title_game.pb))}</small>
                    {/if}
                {:else}
                    <div class="ch live-tag">in progress</div>
                    {#if top}<small>{nameOf(top.h)} leads at {top.w}-{top.l}</small>{/if}
                {/if}
                <div class="meta">
                    {s.format.teams} teams · {s.format.scoring}
                    {#if s.format.era === 'yahoo'}· Yahoo{/if}
                </div>
            </a>
        {/each}
    </div>

    <p class="foot">
        Each season has its own page: final standings, every matchup, the playoff bracket, the draft
        board, the trades and that year's awards. See also
        <a href="/all-time">the all-time table</a>
        and <a href="/record-book">the record book</a>{#if unclaimed?.length},
        and <a href="/unclaimed">the unclaimed teams</a>{/if}.
    </p>
</div>

<style>
    .holder { max-width: 1040px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .note { text-align: center; opacity: 0.78; font-size: 0.9em; line-height: 1.55;
        max-width: 46em; margin: 0 auto 1.2em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 0.6em; }
    .card { display: block; border: 1px solid rgba(127,127,127,0.28); border-radius: 12px;
        padding: 0.7em 0.8em; color: inherit; text-decoration: none; transition: border-color 140ms; }
    .card:hover { border-color: #3498db; }
    .card.live { border-color: #27ae60; background: rgba(39, 174, 96, 0.1); }
    .yr { font-size: 1.5em; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1.1; }
    .ch { display: flex; align-items: center; gap: 0.35em; font-weight: 700; margin-top: 0.15em; }
    .ch span { font-size: 0.95em; }
    .live-tag { color: #27ae60; }
    .card small { display: block; font-size: 0.8em; opacity: 0.75; line-height: 1.35; margin-top: 0.1em; }
    .meta { font-size: 0.76em; opacity: 0.62; margin-top: 0.4em; }
    .foot { margin-top: 2em; font-size: 0.85em; opacity: 0.72; text-align: center; line-height: 1.6; }
    .foot a { color: #3498db; }
</style>
