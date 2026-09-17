<script>
    import { onMount } from 'svelte';
    import { nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    let data = null, error = '', ready = false;
    let season = 'all', who = '';
    onMount(async () => {
        ready = true;
        try { data = await fetch('/data/trades.json').then(r => r.json()); }
        catch (e) { error = 'Could not load the trade history.'; }
        const w = new URLSearchParams(location.search).get('who');
        if (w) who = w;
    });

    $: seasons = data ? [...new Set(data.trades.map(t => t.season))].sort((a, b) => b - a) : [];
    $: people = data ? Object.keys(data.managers).sort((a, b) => nameOf(a).localeCompare(nameOf(b))) : [];
    $: shown = data ? data.trades.filter(t => (season === 'all' || t.season === +season) && (!who || who in t.sides)).slice().reverse() : [];
    $: lopsided = data ? [...data.trades].filter(t => !t.live && t.winner).sort((a, b) => b.margin - a.margin).slice(0, 5) : [];
    $: table = data ? Object.entries(data.managers).map(([h, m]) => ({ h, ...m, net: Math.round((m.in - m.out) * 10) / 10 }))
        .sort((a, b) => b.net - a.net) : [];
    $: netBars = table.map(r => ({ label: nameOf(r.h), value: r.net, note: `${r.w}-${r.l}${r.t ? '-' + r.t : ''}`, highlight: ready && r.h === $myTeam }));
    const sideLine = (s) => [...s.got.map(g => `${g.n}${g.p ? ' ' + g.p : ''}`), ...s.picks].join(', ') || 'nothing listed';
</script>

<div class="holder">
    <h1>Trade Grades</h1>
    {#if data}
        <p class="sub">Every trade since {data.first_season}, graded by what each side actually got out of it:
            the points each acquired player scored <b>in that manager's starting lineup</b> from the trade week on{data.dynasty ? ', in every later season he stayed there' : ', for the rest of that season'}.
            Bench points don't count. {data.dynasty ? 'Draft picks and FAAB are listed but not scored.' : ''} Trades from {site.season} are still being scored.</p>

        <h2>Net points from trading</h2>
        <p class="note">Points gained from players received, minus points the other side got. The number after each name is that manager's trade record.</p>
        <HBarChart items={netBars} format={(v) => (v > 0 ? `+${v}` : `${v}`)} ariaLabel="Net points from trades by manager" />

        <div class="scroll">
            <table>
                <thead><tr><th>Manager</th><th class="num">Trades</th><th class="num">Won-Lost-Even</th><th class="num">Points in</th><th class="num">Points out</th><th>Traded most with</th></tr></thead>
                <tbody>
                    {#each table as r}
                        <tr class:mine={ready && r.h === $myTeam}>
                            <td>{#if managerLink(r.h)}<a href={managerLink(r.h)}>{nameOf(r.h)}</a>{:else}{nameOf(r.h)}{/if}</td>
                            <td class="num">{r.n}</td><td class="num">{r.w}-{r.l}-{r.t}</td>
                            <td class="num">{r.in}</td><td class="num">{r.out}</td>
                            <td>{r.partner?.[0] ? `${nameOf(r.partner[0])} (${r.partner[1]})` : '—'}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <h2>Most lopsided trades</h2>
        {#each lopsided as t}
            <div class="trade lop">
                <div class="head"><b>{t.season}{t.week ? `, week ${t.week}` : ''}</b><span class="win">{nameOf(t.winner)} won by {t.margin}</span></div>
                {#each Object.entries(t.sides) as [h, s]}
                    <p class:winner={h === t.winner}><b>{nameOf(h)}</b> got {sideLine(s)} <span class="val">{s.value} pts</span></p>
                {/each}
            </div>
        {/each}

        <h2>Every trade</h2>
        <div class="filters">
            <select bind:value={season}><option value="all">All seasons</option>{#each seasons as s}<option value={s}>{s}</option>{/each}</select>
            <select bind:value={who}><option value="">Everyone</option>{#each people as p}<option value={p}>{nameOf(p)}</option>{/each}</select>
            {#if ready && $myTeam && who !== $myTeam}<button on:click={() => (who = $myTeam)}>Mine</button>{/if}
            <span class="count">{shown.length} trades</span>
        </div>
        {#each shown as t}
            <div class="trade" class:mine={ready && $myTeam in t.sides}>
                <div class="head">
                    <b>{t.season}{t.week ? `, week ${t.week}` : ''}</b>
                    {#if t.live}<span class="live">still being scored</span>
                    {:else if t.winner}<span class="win">{nameOf(t.winner)} won by {t.margin}</span>
                    {:else}<span class="even">even</span>{/if}
                </div>
                {#each Object.entries(t.sides) as [h, s]}
                    <div class="side" class:winner={h === t.winner && !t.live}>
                        <b>{nameOf(h)}</b> got
                        {#each s.got as g, i}{i ? ', ' : ' '}<span title="{g.st} starts">{g.n}{g.p ? ` (${g.p})` : ''} <small>{g.pts}</small></span>{/each}
                        {#each s.picks as pk}<span class="pick">{pk}</span>{/each}
                        <span class="val">{s.value} pts</span>
                    </div>
                {/each}
            </div>
        {/each}
    {:else if error}
        <p class="sub">{error}</p>
    {:else}
        <p class="sub">Loading trades…</p>
    {/if}
</div>

<style>
    .holder { max-width: 900px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.9em; white-space: nowrap; }
    td a { color: inherit; font-weight: 600; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .filters { display: flex; gap: 0.5em; flex-wrap: wrap; align-items: center; margin: 0.6em 0; }
    select, .filters button { padding: 0.3em 0.5em; font-size: 0.95em; }
    .count { opacity: 0.7; font-size: 0.85em; }
    .trade { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.55em 0.8em; margin: 0.5em 0; font-size: 0.9em; }
    .trade.mine { border-color: #27ae60; }
    .head { display: flex; justify-content: space-between; gap: 1em; margin-bottom: 0.2em; }
    .win { color: #27ae60; font-weight: 700; }
    .even, .live { opacity: 0.7; font-style: italic; }
    .side, .trade p { margin: 0.2em 0; line-height: 1.5; }
    .winner { color: #2ecc71; }
    small { opacity: 0.7; }
    .pick { margin-left: 0.4em; padding: 0 0.35em; border-radius: 3px; background: #34495e; color: #fff; font-size: 0.8em; }
    .val { float: right; font-weight: 700; font-variant-numeric: tabular-nums; }
</style>
