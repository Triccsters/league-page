<script>
    import { onMount } from 'svelte';
    import { nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    let data = null, error = '', ready = false;
    let season = 'all', who = '';
    // Pick value by round: what a pick in each round has returned on average in this league (picks: [season, round, pick, manager, player, pos, value, live, ...])
    let drafts = null;
    $: pickValue = (() => {
        if (!drafts?.picks) return [];
        const m = {};
        for (const p of drafts.picks) { if (p[7]) continue; (m[p[1]] ||= []).push(p[6] || 0); }
        return Object.entries(m).map(([r, v]) => ({ r: +r, n: v.length, avg: Math.round(v.reduce((a, b) => a + b, 0) / v.length) })).filter((x) => x.n >= 3).sort((a, b) => a.r - b.r).slice(0, 18);
    })();
    onMount(async () => {
        ready = true;
        try { data = await fetch('/data/trades.json').then(r => r.json()); }
        catch (e) { error = 'Could not load the trade history.'; }
        try { drafts = await fetch('/data/drafts.json').then(r => r.json()); } catch (e) { drafts = null; }
        const w = new URLSearchParams(location.search).get('who');
        if (w) who = w;
    });

    $: seasons = data ? [...new Set(data.trades.map(t => t.season))].sort((a, b) => b - a) : [];
    $: people = data ? Object.keys(data.managers).sort((a, b) => nameOf(a).localeCompare(nameOf(b))) : [];
    // Trade matrix (T.J., 2026-11-11): trades between each pair of managers.
    // Managers are keyed by handle, which the build resolves from user_id.
    let pair = null;
    $: counts = (() => {
        const c = {};
        if (!data) return c;
        for (const t of data.trades) {
            const hs = Object.keys(t.sides);
            for (const a of hs) for (const b of hs) if (a !== b) {
                c[a] = c[a] || {};
                c[a][b] = (c[a][b] || 0) + 1;
            }
        }
        return c;
    })();
    $: maxPair = Math.max(1, ...Object.values(counts).flatMap(r => Object.values(r)));
    // only where there is more than one season of trades to show
    $: showMatrix = seasons.length > 1;
    const shade = (n, max) => `hsl(145, 63%, ${Math.round(20 + 24 * (max > 1 ? (n - 1) / (max - 1) : 1))}%)`;
    const pick = (a, b) => {
        pair = pair && pair.includes(a) && pair.includes(b) ? null : [a, b];
        if (pair) { who = ''; season = 'all'; document.getElementById('every-trade')?.scrollIntoView({ behavior: 'smooth' }); }
    };
    $: shown = data ? data.trades.filter(t => (season === 'all' || t.season === +season) && (!who || who in t.sides) && (!pair || (pair[0] in t.sides && pair[1] in t.sides))).slice().reverse() : [];
    $: lopsided = data ? [...data.trades].filter(t => !t.live && t.winner).sort((a, b) => b.margin - a.margin).slice(0, 5) : [];
    $: table = data ? Object.entries(data.managers).map(([h, m]) => ({ h, ...m, net: Math.round((m.in - m.out) * 10) / 10 }))
        .sort((a, b) => b.net - a.net) : [];
    $: netBars = table.map(r => ({ label: nameOf(r.h), value: r.net, note: `${r.w}-${r.l}${r.t ? '-' + r.t : ''}`, highlight: ready && r.h === $myTeam }));
    // Letter grade: this side's share of all the points in the trade. Withheld while the trade is still being scored.
    // a used pick reads '2026 round 1: Player POS (1.06), pts'; one still to be made has no colon
    const openPick = (t) => Object.values(t.sides).some((x) => (x.picks || []).some((pk) => !String(pk).includes(':')));
    const letterOf = (t, h) => {
        if (t.live || openPick(t)) return null;
        const vals = Object.values(t.sides).map((x) => x.value || 0);
        const tot = vals.reduce((a, b) => a + b, 0);
        if (tot <= 0) return 'C';   // finished and nobody started anyone: even
        const share = Math.min(1, ((t.sides[h].value || 0) / tot) * (vals.length / 2));
        return share >= 0.68 ? 'A+' : share >= 0.6 ? 'A' : share >= 0.55 ? 'B' : share > 0.45 ? 'C' : share > 0.4 ? 'D' : 'F';
    };
    const sideLine = (s) => [...s.got.map(g => `${g.n}${g.p ? ' ' + g.p : ''}`), ...s.picks].join(', ') || 'nothing listed';
</script>

<div class="holder">
    <h1>Trade Grades</h1>
    {#if data}
        <p class="sub">Every trade since {data.first_season}, graded by what each side actually got out of it:
            the points each acquired player scored <b>in that manager's starting lineup</b> from the trade week on{data.dynasty ? ', in every later season he stayed there' : ', for the rest of that season'}.
            Bench points don't count. {data.dynasty ? 'A rookie draft pick counts for what the drafted player scored in the lineup of the manager who got the pick and used it. Picks that were traded on again, startup draft picks and FAAB are listed but not scored.' : ''} Trades from {site.season} are still being scored.</p>

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

        {#if showMatrix}
            <h2>Trade matrix</h2>
            <p class="note">How many trades each pair of managers has made since {data.first_season}. Brighter means more. Tap a number to see those trades below.</p>
            <div class="scroll">
                <table class="matrix">
                    <thead>
                        <tr>
                            <th></th>
                            {#each people as c}<th class="mh" class:me={ready && c === $myTeam}><span>{nameOf(c)}</span></th>{/each}
                        </tr>
                    </thead>
                    <tbody>
                        {#each people as r}
                            <tr>
                                <th class="rh" class:me={ready && r === $myTeam}>{nameOf(r)}</th>
                                {#each people as c}
                                    {#if r === c}
                                        <td class="self"></td>
                                    {:else if counts[r]?.[c]}
                                        <td class="cell"><button class="mx" class:on={pair && pair.includes(r) && pair.includes(c)}
                                            style="background: {shade(counts[r][c], maxPair)}"
                                            aria-label="{nameOf(r)} and {nameOf(c)}: {counts[r][c]} trades"
                                            on:click={() => pick(r, c)}>{counts[r][c]}</button></td>
                                    {:else}
                                        <td class="cell zero">·</td>
                                    {/if}
                                {/each}
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}

        <h2>Most lopsided trades</h2>
        {#each lopsided as t}
            <div class="trade lop">
                <div class="head"><b>{t.season}{t.week ? `, week ${t.week}` : ''}</b><span class="win">{nameOf(t.winner)} won by {t.margin}</span></div>
                {#each Object.entries(t.sides) as [h, s]}
                    <p class:winner={h === t.winner}><b>{nameOf(h)}</b> got {sideLine(s)} <span class="val">{s.value} pts</span></p>
                {/each}
            </div>
        {/each}

        {#if pickValue.length}
            <h2>What a pick is worth</h2>
            <p class="note">Average points a pick in each round has returned in its manager's starting lineup, across every finished draft in this league. Use it to judge a trade for picks.</p>
            <div class="pv">{#each pickValue as v}<div class:early={v.r <= 2}><small>Rd {v.r}</small><b>{v.avg}</b><small>{v.n} picks</small></div>{/each}</div>
        {/if}

        <h2 id="every-trade">Every trade</h2>
        <p class="key">Letter = that side's share of the points in the trade. A+ 68% or more · A 60% · B 55% · C about even · D 45% or less · F 40% or less. ⏳ means the grade is pending: the trade is still being scored, or it includes a draft pick that has not been used yet.</p>
        {#if pair}
            <p class="pairbar">Showing trades between <b>{nameOf(pair[0])}</b> and <b>{nameOf(pair[1])}</b>
                <button on:click={() => (pair = null)}>Show all</button></p>
        {/if}
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
                    {@const L = letterOf(t, h)}
                    <div class="side" class:winner={h === t.winner && !t.live}>
                        <span class="ltr {L ? 'g' + L[0] : 'gp'}" title={L ? 'Share of the points in this trade' : openPick(t) ? 'Grade pending: a pick in this trade has not been used yet' : 'Grade pending: still being scored'}>{L || '⏳'}</span>
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
    .ltr { display: inline-block; min-width: 2em; text-align: center; font-weight: 800; font-size: 0.85em; border-radius: 6px; padding: 0.1em 0.3em; margin-right: 0.4em; color: #fff; background: #555; }
    .ltr.gA { background: #1e8449; } .ltr.gB { background: #2471a3; } .ltr.gC { background: #7d6608; } .ltr.gD { background: #af601a; } .ltr.gF { background: #a93226; } .ltr.gp { background: #444; }
    .pv { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 0.4em; }
    .pv div { text-align: center; border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.4em 0.2em; background: rgba(127,127,127,0.06); }
    .pv div.early { border-color: #d4af37; }
    .pv b { display: block; font-size: 1.25em; } .pv small { display: block; opacity: 0.7; font-size: 0.75em; }
    .key { text-align: center; font-size: 0.85em; opacity: 0.8; margin: 0.3em 0 0.8em; }
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
    .matrix { width: auto; margin: 0 auto; }
    .matrix th, .matrix td { padding: 2px; border: 0; text-align: center; }
    .matrix .rh { text-align: right; padding-right: 0.5em; font-weight: 600; }
    .matrix .mh { vertical-align: bottom; height: 6.5em; font-weight: 600; }
    .matrix .mh span { writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; }
    .matrix .me { color: #2ecc71; }
    .matrix .self { background: rgba(127,127,127,0.28); border-radius: 4px; }
    .matrix .zero { opacity: 0.35; }
    .mx { width: 2.1em; height: 2.1em; padding: 0; border: 2px solid transparent; border-radius: 4px; color: #ffffff; font-weight: 700; font-size: 0.95em; cursor: pointer; font-variant-numeric: tabular-nums; }
    .mx.on { border-color: #ffffff; outline: 2px solid #27ae60; }
    .pairbar { margin: 0.6em 0 0; padding: 0.45em 0.7em; border-radius: 6px; background: #1e8449; color: #ffffff; font-size: 0.92em; }
    .pairbar button { margin-left: 0.6em; padding: 0.15em 0.6em; font-size: 0.95em; }
</style>
