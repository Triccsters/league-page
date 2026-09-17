<script>
    // Drag through a season and watch the table sort itself out week by week.
    import { onMount, onDestroy } from 'svelte';
    import { flip } from 'svelte/animate';
    import { games, nameOf, teamName, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });

    const reg = games.filter(g => !g.playoff);
    const seasons = [...new Set(reg.map(g => g.season))].sort((a, b) => b - a);
    const curWeeks = new Set(reg.filter(g => g.season === site.season).map(g => g.week)).size;
    let season = seasons[0] === site.season && curWeeks < 2 && seasons[1] ? seasons[1] : seasons[0];

    let week = 1;
    let playing = false;
    let timer = null;

    $: weeks = [...new Set(reg.filter(g => g.season === +season).map(g => g.week))].sort((a, b) => a - b);
    $: lastWeek = weeks.length ? weeks[weeks.length - 1] : 1;
    // when the season changes, jump to the end of it
    $: if (season) week = Math.min(week, lastWeek) || 1;

    function table(s, through) {
        const t = {};
        const row = (h) => (t[h] ||= { h, w: 0, l: 0, pf: 0, pa: 0, last: [] });
        for (const g of reg.filter(g => g.season === s && g.week <= through)) {
            for (const [me, mp, op] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
                const r = row(me);
                r.pf += mp;
                r.pa += op;
                if (mp > op) { r.w++; r.last.push('W'); }
                else if (mp < op) { r.l++; r.last.push('L'); }
            }
        }
        return Object.values(t)
            .map(r => ({ ...r, pf: Math.round(r.pf * 100) / 100, pct: r.w + r.l ? r.w / (r.w + r.l) : 0 }))
            .sort((a, b) => b.w - a.w || b.pf - a.pf);
    }

    $: rows = table(+season, week);
    $: maxPf = rows.length ? Math.max(...rows.map(r => r.pf)) : 1;

    // where each team sat a week ago, so movement can be shown
    $: prev = week > 1 ? table(+season, week - 1) : [];
    $: prevRank = Object.fromEntries(prev.map((r, i) => [r.h, i + 1]));

    function play() {
        stop();
        if (week >= lastWeek) week = 1;
        playing = true;
        timer = setInterval(() => {
            if (week >= lastWeek) { stop(); return; }
            week += 1;
        }, 850);
    }
    function stop() {
        playing = false;
        if (timer) clearInterval(timer);
        timer = null;
    }
    onDestroy(stop);

    const label = (h) => teamName(+season, h) || nameOf(h);
    const move = (h) => (prevRank[h] ? prevRank[h] - (rows.findIndex(r => r.h === h) + 1) : 0);
</script>

<div class="holder">
    <h1>Season Ladder</h1>
    <p class="sub">
        Drag the slider, or hit play, and watch the table reorder itself week by week. Ranked by record, then
        points, the way the standings are. The arrow is the move since the week before.
    </p>

    <div class="controls">
        <select bind:value={season} onchange={() => { stop(); week = 1; }}>
            {#each seasons as s}<option value={s}>{s}{s === site.season ? ' (so far)' : ''}</option>{/each}
        </select>
        <button onclick={() => (playing ? stop() : play())}>{playing ? '❚❚ Pause' : '▶ Play'}</button>
        <input type="range" min="1" max={lastWeek} bind:value={week} oninput={stop} aria-label="Week" />
        <span class="wk">Week {week}</span>
    </div>

    <ol class="ladder">
        {#each rows as r, i (r.h)}
            <li animate:flip={{ duration: 420 }} class:mine={ready && r.h === $myTeam}>
                <span class="rk">{i + 1}</span>
                <span class="mv" class:up={move(r.h) > 0} class:down={move(r.h) < 0}>
                    {move(r.h) > 0 ? `▲${move(r.h)}` : move(r.h) < 0 ? `▼${-move(r.h)}` : ''}
                </span>
                <span class="nm">
                    {#if managerLink(r.h)}<a href={managerLink(r.h)}>{label(r.h)}</a>{:else}{label(r.h)}{/if}
                    <small>{nameOf(r.h)}</small>
                </span>
                <span class="rec">{r.w}-{r.l}</span>
                <span class="bar"><span class="fill" style="width: {(100 * r.pf) / maxPf}%"></span></span>
                <span class="pf">{Math.round(r.pf)}</span>
            </li>
        {/each}
    </ol>
</div>

<style>
    .holder { max-width: 900px; margin: 0 auto 3em; padding: 0 1em; text-align: left; }
    h1 { margin-bottom: 0.2em; }
    .sub { opacity: 0.75; font-size: 0.9em; max-width: 58em; }
    .controls { display: flex; align-items: center; gap: 0.6em; flex-wrap: wrap; margin: 1.2em 0 0.8em; }
    select, button { font: inherit; font-size: 0.9em; padding: 0.3em 0.7em; border-radius: 6px;
                     border: 1px solid rgba(127,127,127,0.4); background: transparent; color: inherit; cursor: pointer; }
    input[type="range"] { flex: 1 1 220px; accent-color: #3498db; }
    .wk { font-variant-numeric: tabular-nums; font-weight: 700; min-width: 5.5em; }
    .ladder { list-style: none; margin: 0; padding: 0; }
    li { display: grid; grid-template-columns: 2em 2.4em minmax(120px, 1fr) 3.4em minmax(60px, 2fr) 3.2em;
         align-items: center; gap: 0.5em; padding: 0.35em 0.4em; border-radius: 7px;
         border-bottom: 1px solid rgba(127,127,127,0.16); font-size: 0.92em; }
    li.mine { background: rgba(52,152,219,0.14); }
    .rk { opacity: 0.6; text-align: right; font-variant-numeric: tabular-nums; }
    .mv { font-size: 0.72em; opacity: 0.9; }
    .mv.up { color: #27ae60; }
    .mv.down { color: #e74c3c; }
    .nm small { display: block; opacity: 0.6; font-size: 0.78em; }
    .nm a { color: #3498db; }
    .rec { font-variant-numeric: tabular-nums; font-weight: 700; }
    .bar { height: 9px; border-radius: 99px; background: rgba(127,127,127,0.2); overflow: hidden; }
    .fill { display: block; height: 100%; background: #3498db; border-radius: 99px;
            transition: width 380ms cubic-bezier(0.22,0.85,0.25,1); }
    .pf { text-align: right; font-variant-numeric: tabular-nums; opacity: 0.8; }
    @media (max-width: 560px) {
        li { grid-template-columns: 1.8em 2.2em 1fr 3.2em 2.8em; }
        .bar { display: none; }
    }
    @media (prefers-reduced-motion: reduce) {
        .fill { transition: none; }
    }
</style>
