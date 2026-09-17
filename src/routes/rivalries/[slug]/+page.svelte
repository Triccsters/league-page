<script>
    import { rivalry, nameOf, pairFromSlug, site, hasYahoo } from '$lib/utils/flpHistory';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';
    export let data;

    $: [x, y] = pairFromSlug(data.slug);
    $: r = rivalry(x, y);
    $: X = nameOf(x);
    $: Y = nameOf(y);
    $: n = r.meetings.length;

    // Running-wins chart
    const W = 640, H = 220, L = 36, R = 12, T = 12, B = 28;
    $: top = Math.max(2, r.all.x, r.all.y);
    $: px = (i) => L + (i * (W - L - R)) / Math.max(1, n - 1);
    $: py = (v) => T + (H - T - B) * (1 - v / top);
    $: line = (key) => r.running.map((p, i) => `${i ? 'L' : 'M'}${px(i).toFixed(1)},${py(p[key]).toFixed(1)}`).join(' ');
    $: eraSplit = hasYahoo ? r.meetings.findIndex(m => m.era !== 'yahoo') : -1;
    $: margins = [...r.meetings].reverse().map(m => ({
        label: `${m.season} ${m.label || (m.playoff ? 'Playoffs' : 'Wk ' + m.week)}`,
        value: Math.round((m.xp - m.yp) * 100) / 100,
        note: `${m.xp.toFixed(1)}–${m.yp.toFixed(1)}`,
        color: m.xp >= m.yp ? '#3498db' : '#e74c3c',
        highlight: m.season === site.season,
    }));

    const rec = (t) => `${t.x}–${t.y}${t.t ? `–${t.t}` : ''}`;
    const gameName = (m) => m.label || (m.playoff ? 'Playoffs' : `Week ${m.week}`);
</script>

<svelte:head><title>{X} vs {Y} | {site.league_name} rivalries</title></svelte:head>

<div class="holder">
    <p class="back"><a href="/rivalries">← All rivalries</a></p>
    <h1>{X} <span class="vs">vs</span> {Y}</h1>

    {#if n === 0}
        <p class="sub">These two have never played each other.</p>
    {:else}
        <div class="big">
            <div class:lead={r.all.x > r.all.y}><b>{r.all.x}</b><span>{X}</span><YourTeamBadge handle={x} size="small" /></div>
            <div class="mid">{n} meetings{r.all.t ? ` · ${r.all.t} tie` : ''}</div>
            <div class:lead={r.all.y > r.all.x}><b>{r.all.y}</b><span>{Y}</span><YourTeamBadge handle={y} size="small" /></div>
        </div>

        {#if r.streak}
            <p class="line">{nameOf(r.streak.who)} has won the last {r.streak.n === 1 ? 'meeting' : r.streak.n}{r.streak.n > 1 ? ' in a row' : ''}.</p>
        {/if}
        {#if r.finals.length}
            <p class="line"><b>Met in {r.finals.length === 1 ? 'a final' : `${r.finals.length} finals`}:</b>
                {#each r.finals as f, i}{i ? ', ' : ''}{f.season} ({nameOf(f.winner)} won {Math.max(f.xp, f.yp)}–{Math.min(f.xp, f.yp)}){/each}.</p>
        {/if}

        <table class="split">
            <thead><tr><th></th><th>{X}–{Y}</th><th>Points</th></tr></thead>
            <tbody>
                <tr><td>All games</td><td>{rec(r.all)}</td><td>{r.all.xpts} – {r.all.ypts}</td></tr>
                <tr><td>Regular season</td><td>{rec(r.regular)}</td><td>{r.regular.xpts} – {r.regular.ypts}</td></tr>
                <tr><td>Playoffs and consolation</td><td>{rec(r.playoffs)}</td><td>{r.playoffs.xpts} – {r.playoffs.ypts}</td></tr>
                {#if hasYahoo}
                    <tr><td>Yahoo era ({site.yahoo_years[0]}–{site.yahoo_years[1]})</td><td>{rec(r.yahoo)}</td><td>{r.yahoo.xpts} – {r.yahoo.ypts}</td></tr>
                    <tr><td>Sleeper era ({site.sleeper_from}–now)</td><td>{rec(r.sleeper)}</td><td>{r.sleeper.xpts} – {r.sleeper.ypts}</td></tr>
                {/if}
            </tbody>
        </table>

        <div class="facts">
            {#if r.closest}<div><span>Closest game</span><b>{r.closest.season} {gameName(r.closest)}</b>{nameOf(r.closest.winner)} by {r.closest.margin}</div>{/if}
            {#if r.biggest}<div><span>Biggest blowout</span><b>{r.biggest.season} {gameName(r.biggest)}</b>{nameOf(r.biggest.winner)} by {r.biggest.margin}</div>{/if}
        </div>

        <h2>Running wins</h2>
        <svg viewBox="0 0 {W} {H}" role="img" aria-label="Running wins: {X} {r.all.x}, {Y} {r.all.y}">
            {#if eraSplit > 0}
                <line x1={px(eraSplit)} x2={px(eraSplit)} y1={T} y2={H - B} class="era" />
                <text x={px(eraSplit) + 4} y={T + 12} class="tick">Sleeper →</text>
            {/if}
            <line x1={L} x2={W - R} y1={H - B} y2={H - B} class="axis" />
            <text x={L - 6} y={py(top) + 4} class="tick" text-anchor="end">{top}</text>
            <text x={L - 6} y={py(0) + 4} class="tick" text-anchor="end">0</text>
            <text x={L} y={H - 8} class="tick">{r.meetings[0].season}</text>
            <text x={W - R} y={H - 8} class="tick" text-anchor="end">{r.meetings[n - 1].season}</text>
            <path d={line('y')} class="ln red" />
            <path d={line('x')} class="ln blue" />
        </svg>
        <p class="keys"><span><i class="sw blue"></i>{X}</span><span><i class="sw red"></i>{Y}</span></p>

        <h2>Margin in every meeting</h2>
        <p class="sub">Newest first. Blue bars are {X} wins, red bars are {Y} wins. Green labels and rows are {site.season} games.</p>
        <HBarChart items={margins} format={(v) => (v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1))} ariaLabel="Margin of every meeting between {X} and {Y}" />

        <h2>Every meeting</h2>
        <table class="log">
            <thead><tr><th>#</th><th>Season</th><th>Game</th><th class="num">{X}</th><th class="num">{Y}</th><th>Winner</th></tr></thead>
            <tbody>
                {#each [...r.meetings].reverse() as m, i}
                    <tr class:po={m.playoff} class:live={m.season === site.season}>
                        <td>{n - i}</td>
                        <td>{m.season}{#if m.season === site.season} <span class="now">this season</span>{:else if hasYahoo} <small>{m.eraLabel}</small>{/if}</td>
                        <td>{gameName(m)}</td>
                        <td class="num" class:win={m.winner === x}>{m.xp.toFixed(2)}</td>
                        <td class="num" class:win={m.winner === y}>{m.yp.toFixed(2)}</td>
                        <td>{m.winner ? nameOf(m.winner) : 'Tie'} <small>+{m.margin}</small></td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
</div>

<style>
    .holder { max-width: 820px; margin: 0 auto; padding: 1.5em 1em; }
    .back a { color: inherit; opacity: 0.75; }
    h1 { text-align: center; margin: 0.2em 0 0.6em; }
    .vs { opacity: 0.5; font-weight: 400; }
    .sub { text-align: center; opacity: 0.7; }
    .big { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; text-align: center; gap: 1em; }
    .big b { display: block; font-size: 2.8em; line-height: 1; font-variant-numeric: tabular-nums; }
    .big .mid { opacity: 0.7; }
    .lead b { color: #27ae60; }
    .line { text-align: center; margin: 0.4em 0; }
    h2 { margin-top: 1.6em; border-bottom: 2px solid rgba(127,127,127,0.3); padding-bottom: 0.2em; font-size: 1.15em; }
    table { width: 100%; border-collapse: collapse; margin-top: 0.8em; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.25); text-align: left; font-size: 0.93em; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .win { font-weight: 700; color: #27ae60; }
    tr.po td { background: rgba(142, 68, 173, 0.12); }
    tr.live td { background: rgba(39, 174, 96, 0.14); }
    .now { font-size: 0.72em; font-weight: 600; color: #2ecc71; white-space: nowrap; }
    small { opacity: 0.6; }
    .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.8em; margin-top: 1em; }
    .facts div { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.7em; text-align: center; }
    .facts span { display: block; font-size: 0.8em; opacity: 0.7; text-transform: uppercase; }
    .facts b { display: block; }
    svg { width: 100%; height: auto; }
    .axis { stroke: currentColor; opacity: 0.3; }
    .era { stroke: currentColor; opacity: 0.35; stroke-dasharray: 4 4; }
    .tick { fill: currentColor; opacity: 0.7; font-size: 12px; }
    .ln { fill: none; stroke-width: 3; }
    .blue { stroke: #3498db; }
    .red { stroke: #e74c3c; }
    .keys { display: flex; justify-content: center; gap: 1.5em; }
    .keys span { display: inline-flex; align-items: center; gap: 0.4em; }
    .sw { display: inline-block; width: 14px; height: 14px; border-radius: 50%; }
    .sw.blue { background: #3498db; }
    .sw.red { background: #e74c3c; }
</style>
