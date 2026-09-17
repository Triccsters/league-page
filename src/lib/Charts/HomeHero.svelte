<script>
    // What is happening right now, above the fold: your game this week, where you
    // stand, the game worth watching, and what last week produced.
    import { onMount } from 'svelte';
    import { games, nameOf, teamName, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import previews from '$lib/data/previews.json';
    import odds from '$lib/data/odds.json';

    let ready = false;
    onMount(() => { ready = true; });

    const week = previews?.week ?? null;
    const list = previews?.games ?? [];
    const byHandle = Object.fromEntries((odds?.teams ?? []).map(t => [t.h, t]));

    const label = (h) => teamName(site.season, h) || nameOf(h);

    // the viewer's own game
    $: mine = !ready || !$myTeam ? null : list.find(g => g.a === $myTeam || g.b === $myTeam);
    $: me = !mine ? null : ($myTeam === mine.a
        ? { him: mine.a, them: mine.b, win: mine.a_win }
        : { him: mine.b, them: mine.a, win: Math.round((100 - mine.a_win) * 10) / 10 });
    $: standing = me ? byHandle[me.him] : null;

    // The closest game on the board, but never the one already shown above as
    // the viewer's own game.
    const closest = (pool) => (pool.length
        ? pool.reduce((b, g) => (Math.abs(g.a_win - 50) < Math.abs(b.a_win - 50) ? g : b))
        : null);
    $: marquee = closest(mine ? list.filter(g => g !== mine) : list);

    // what last week actually produced
    const lastWeek = (() => {
        const reg = games.filter(g => g.season === site.season);
        if (!reg.length) return null;
        const w = Math.max(...reg.map(g => g.week));
        const rows = [];
        for (const g of reg.filter(g => g.week === w)) {
            rows.push([g.a, g.pa], [g.b, g.pb]);
        }
        if (!rows.length) return null;
        rows.sort((x, y) => y[1] - x[1]);
        return { week: w, top: rows[0], low: rows[rows.length - 1] };
    })();
</script>

{#if week && list.length}
    <section class="hero">
        <div class="head">
            <span class="wk">Week {week}</span>
            {#if previews.playoff}<span class="tag">Playoffs</span>{/if}
        </div>

        {#if previews.league_note}
            <div class="note">
                {#each previews.league_note.split('\n').filter(Boolean) as para}
                    <p>{para}</p>
                {/each}
                {#if previews.byline}<p class="by">{previews.byline}</p>{/if}
            </div>
        {/if}

        <div class="grid">
            {#if me}
                <div class="card mine">
                    <h3>Your week {week}</h3>
                    <p class="vs">
                        <b>{label(me.him)}</b>
                        <span class="v">vs</span>
                        {#if managerLink(me.them)}<a href={managerLink(me.them)}>{label(me.them)}</a>{:else}{label(me.them)}{/if}
                    </p>
                    <div class="meter" aria-label="Win chance {me.win}%">
                        <div class="fill" style="width: {me.win}%"></div>
                    </div>
                    <p class="line"><b>{me.win}%</b> chance to win</p>
                    {#if standing}
                        <p class="line sub">
                            {standing.w}-{standing.l} · playoff odds <b>{standing.playoff}%</b>
                        </p>
                    {/if}
                    {#if mine.note}
                        <p class="flag">{mine.note}</p>
                    {:else if mine.flags?.length}
                        <p class="flag">{mine.flags[0].replace(/\{([^}]+)\}/g, (_, h) => nameOf(h))}</p>
                    {/if}
                </div>
            {:else}
                <div class="card">
                    <h3>This week</h3>
                    <p class="line sub">Pick your name at the top and this becomes your own matchup, every week.</p>
                    <p class="line"><a href="/preview">See all {list.length} previews →</a></p>
                </div>
            {/if}

            {#if marquee}
                <div class="card">
                    <h3>Game of the week</h3>
                    <p class="vs">
                        <b>{label(marquee.a)}</b><span class="v">vs</span><b>{label(marquee.b)}</b>
                    </p>
                    <p class="line sub">The closest call on the board: {marquee.a_win}% / {Math.round((100 - marquee.a_win) * 10) / 10}%</p>
                    {#if marquee.flags?.length}
                        <p class="flag">{marquee.flags[0].replace(/\{([^}]+)\}/g, (_, h) => nameOf(h))}</p>
                    {/if}
                </div>
            {/if}

            {#if lastWeek}
                <div class="card">
                    <h3>Week {lastWeek.week} produced</h3>
                    <p class="line">
                        🏆 <b>{Math.round(lastWeek.top[1] * 100) / 100}</b>
                        {#if managerLink(lastWeek.top[0])}<a href={managerLink(lastWeek.top[0])}>{nameOf(lastWeek.top[0])}</a>{:else}{nameOf(lastWeek.top[0])}{/if}
                    </p>
                    <p class="line sub">
                        💤 {Math.round(lastWeek.low[1] * 100) / 100} {nameOf(lastWeek.low[0])}
                    </p>
                    <p class="line"><a href="/recaps">The recap →</a> · <a href="/what-if">What if →</a></p>
                </div>
            {/if}
        </div>
    </section>
{/if}

<style>
    .hero { max-width: 1000px; margin: 0.5em auto 1.5em; padding: 0 1em; text-align: left; }
    .head { display: flex; align-items: baseline; gap: 0.6em; margin-bottom: 0.5em; }
    .wk { font-size: 1.2em; font-weight: 700; }
    .tag { font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.05em;
           border: 1px solid rgba(231,76,60,0.7); color: #e74c3c; border-radius: 999px; padding: 0.1em 0.6em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.8em; }
    .card { border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; padding: 0.7em 0.9em; }
    .card.mine { border-color: rgba(52,152,219,0.6); background: rgba(52,152,219,0.08); }
    h3 { margin: 0 0 0.3em; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.65; }
    .vs { margin: 0 0 0.4em; font-size: 0.95em; line-height: 1.35; }
    .v { opacity: 0.55; margin: 0 0.4em; font-size: 0.85em; }
    .meter { height: 7px; border-radius: 99px; background: rgba(127,127,127,0.25); overflow: hidden; margin-bottom: 0.4em; }
    .fill { height: 100%; background: #3498db; border-radius: 99px; animation: grow 700ms cubic-bezier(0.22,0.85,0.25,1) both; }
    @keyframes grow { from { width: 0 !important; } }
    .note { margin: 0 0 0.9em; max-width: 62em; }
    .note p { margin: 0 0 0.5em; font-size: 0.95em; line-height: 1.5; }
    .note .by { font-size: 0.8em; opacity: 0.6; font-style: italic; margin-bottom: 0; }
    .line { margin: 0.1em 0; font-size: 0.9em; }
    .line.sub { opacity: 0.7; font-size: 0.82em; }
    .flag { margin: 0.4em 0 0; font-size: 0.78em; opacity: 0.75; font-style: italic; }
    a { color: #3498db; }
    @media (prefers-reduced-motion: reduce) {
        .fill { animation: none; }
    }
</style>
