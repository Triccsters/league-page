<script>
    import { onMount } from 'svelte';
    import { nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    let data = null, error = '', ready = false;
    let season = 'all', who = '';
    // every trade is a long list: show 20, then more on request; any filter change starts over
    let tradeLimit = 20;
    $: season, who, pair, (tradeLimit = 20);
    // Pick value by round: what a pick in each round has returned on average in this league (picks: [season, round, pick, manager, player, pos, value, live, ...])
    let drafts = null;
    $: pickValue = (() => {
        if (!drafts?.picks) return [];
        // a season where round 1 holds more picks than two per manager has lost its round numbers: leave it out
        const r1 = {}, mg = {};
        for (const p of drafts.picks) { (mg[p[0]] ||= new Set()).add(p[3]); if (p[1] === 1) r1[p[0]] = (r1[p[0]] || 0) + 1; }
        const bad = new Set(Object.keys(r1).filter((y) => r1[y] > 2 * mg[y].size).map(Number));
        // one group per draft round, in pick order, so each pick knows whether it was early, mid or late in its round
        const groups = {};
        for (const p of drafts.picks) {
            if (p[7] || bad.has(p[0])) continue;
            if (drafts.dynasty && /startup/i.test(String(p[8] || ''))) continue;
            (groups[`${p[0]}|${p[8]}|${p[1]}`] ||= []).push(p);
        }
        const m = {};
        for (const g of Object.values(groups)) {
            g.sort((x, y) => x[2] - y[2]);
            g.forEach((p, i) => {
                const blank = () => ({ n: 0, v: 0, st: 0, yrs: 0 });
                const e = (m[p[1]] ||= { ...blank(), thirds: [blank(), blank(), blank()] });
                const t = g.length >= 3 ? Math.min(2, Math.floor((3 * i) / g.length)) : 1;
                for (const b of [e, e.thirds[t]]) { b.n++; b.v += p[6] || 0; b.st += p[10] || 0; b.yrs += p[11] || 1; }
            });
        }
        const r1d = (x) => Math.round(x * 10) / 10;
        const shape = (e) => (e.n ? { n: e.n, avg: Math.round(e.v / e.n), perSeason: Math.round(e.v / e.yrs),
            perGame: e.st ? r1d(e.v / e.st) : null, starts: Math.round(e.st / e.n) } : null);
        return Object.entries(m).map(([r, e]) => ({ r: +r, ...shape(e), thirds: e.thirds.map(shape) }))
            .filter((x) => x.n >= 3).sort((a, b) => a.r - b.r).slice(0, 18);
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
    // Letter grades on a curve (T.J., 2026-11-15). Each side's net is its points minus the other
    // side's. Nets inside 10% of the trade are a fair trade, C for both. The rest are ranked against
    // every finished trade in this league: winners A+ to B, the other side the mirror, F to C-.
    // a used pick reads '2026 round 1: Player POS (1.06), pts'; one still to be made is '2027 round 1'
    const openPick = (t) => Object.values(t.sides).some((x) => (x.picks || []).some((pk) => /^\d{4} round \d+$/.test(String(pk).trim())));
    // a side that got only picks or FAAB that are never scored cannot be compared with the other
    // (a rookie pick that IS scored ends in 'pts', even when its player has scored nothing yet)
    const unscored = (t) => Object.values(t.sides).some((x) => !(x.value > 0) && !(x.got || []).length && !(x.picks || []).some((pk) => /pts$/.test(String(pk).trim())));
    const totOf = (t) => Object.values(t.sides).reduce((a, x) => a + (x.value || 0), 0);
    const netOf = (t, h) => {
        const others = Object.keys(t.sides).filter((x) => x !== h);
        return (t.sides[h].value || 0) - others.reduce((a, x) => a + (t.sides[x].value || 0), 0) / Math.max(1, others.length);
    };
    const FAIR = 0.10;
    const graded = (t) => !t.live && !openPick(t) && !unscored(t) && totOf(t) > 0;
    const isFair = (t) => graded(t) && Object.keys(t.sides).every((h) => Math.abs(netOf(t, h)) <= FAIR * totOf(t));
    $: curve = (() => {
        const up = [], down = [];
        for (const t of data?.trades || []) {
            if (!graded(t)) continue;
            for (const h of Object.keys(t.sides)) {
                const n = netOf(t, h);
                if (Math.abs(n) > FAIR * totOf(t)) (n > 0 ? up : down).push(Math.abs(n));
            }
        }
        return { up: up.sort((x, y) => y - x), down: down.sort((x, y) => y - x) };
    })();
    const WIN = [[0.10, 'A+'], [0.30, 'A'], [0.60, 'B+'], [1.01, 'B']];
    const LOSE = [[0.10, 'F'], [0.30, 'D'], [0.60, 'D+'], [1.01, 'C-']];
    $: letterOf = (t, h) => {
        if (t.live || openPick(t)) return null;          // too early
        if (unscored(t)) return 'n/a';
        const tot = totOf(t);
        if (tot <= 0) return 'C';                        // finished and nobody started anyone: even
        const n = netOf(t, h);
        if (Math.abs(n) <= FAIR * tot) return 'C';
        const list = n > 0 ? curve.up : curve.down;
        const place = list.length ? Math.max(0, list.findIndex((x) => x <= Math.abs(n))) / list.length : 0;
        return (n > 0 ? WIN : LOSE).find(([cut]) => place < cut)[1];
    };
    const ltrClass = (L) => (!L || L === 'n/a' ? 'gp' : 'g' + L[0]);
    const ltrTitle = (t, L) => !L ? (openPick(t) ? 'Too early: a pick in this trade has not been used yet' : 'Too early: still being scored')
        : L === 'n/a' ? 'Not graded: one side got only picks or FAAB, which are never scored'
        : L === 'C' ? 'Fair trade: the two sides finished within 10% of the points in it'
        : 'Ranked against every finished trade in this league';
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
            <p class="note">What a pick in each round has returned in its manager's starting lineup, across every finished {drafts?.dynasty ? 'rookie draft' : 'draft'} in this league{drafts?.dynasty ? '. The startup draft is left out. Use it to judge a trade for picks.' : '. It shows what each round of the draft has been worth.'}
                The big number is the average total per pick. Per game is points for each week the player was in the lineup.{drafts?.dynasty ? ' Per season spreads the total over every season since that draft.' : ''} Each round is split into thirds by pick: early, mid and late.</p>
            {#each pickValue as v}
                <div class="pvr" class:early={v.r <= 2}>
                    <div class="pvh"><b>Round {v.r}</b><span>{v.avg} a pick{drafts?.dynasty ? `, ${v.perSeason} a season` : ''}, {v.perGame ?? 'n/a'} a game, across {v.n} picks</span></div>
                    <div class="pv">
                        {#each ['Early', 'Mid', 'Late'] as lab, i}
                            {@const t = v.thirds[i]}
                            <div class="pvc">
                                <small class="lab">{lab}</small>
                                {#if t}
                                    <b>{t.avg}</b>
                                    <small>per pick</small>
                                    <div class="rate">
                                        {#if drafts?.dynasty}<span><b>{t.perSeason}</b> per season</span>{/if}
                                        <span><b>{t.perGame ?? 'n/a'}</b> per game</span>
                                    </div>
                                    <small>{t.n} picks, {t.starts} starts each</small>
                                {:else}
                                    <small>no picks</small>
                                {/if}
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        {/if}

        <h2 id="every-trade">Every trade</h2>
        <p class="key">Letters are graded on a curve against every finished trade in this league. For the side that came out ahead: A+ is the top tenth by points gained, A the next fifth, then B+ and B. The other side gets the mirror: F, D, D+ and C-. C is a fair trade, where the two sides finished within 10% of the points in it. ⏳ is too early: the trade is still being scored, or it includes a draft pick that has not been used. n/a means one side got only picks or FAAB, which are never scored.</p>
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
        {#each shown.slice(0, tradeLimit) as t}
            <div class="trade" class:mine={ready && $myTeam in t.sides}>
                <div class="head">
                    <b>{t.season}{t.week ? `, week ${t.week}` : ''}</b>
                    {#if t.live}<span class="live">still being scored</span>
                    {:else if isFair(t)}<span class="even">fair trade{t.winner ? `, ${nameOf(t.winner)} ahead by ${t.margin}` : ''}</span>
                    {:else if t.winner}<span class="win">{nameOf(t.winner)} won by {t.margin}</span>
                    {:else}<span class="even">even</span>{/if}
                </div>
                {#each Object.entries(t.sides) as [h, s]}
                    {@const L = letterOf(t, h)}
                    <div class="side" class:winner={h === t.winner && !t.live}>
                        <span class="ltr {ltrClass(L)}" title={ltrTitle(t, L)}>{L || '⏳'}</span>
                        <b>{nameOf(h)}</b> got
                        {#each s.got as g, i}{i ? ', ' : ' '}<span title="{g.st} starts">{g.n}{g.p ? ` (${g.p})` : ''} <small>{g.pts}</small></span>{/each}
                        {#each s.picks as pk}<span class="pick">{pk}</span>{/each}
                        <span class="val">{s.value} pts</span>
                    </div>
                {/each}
            </div>
        {/each}
        {#if shown.length > tradeLimit}<p class="moretrades"><button on:click={() => (tradeLimit += 20)}>Show 20 more</button> <button on:click={() => (tradeLimit = shown.length)}>Show all {shown.length}</button></p>{/if}
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
    .pvr { margin: 0.7em 0; padding: 0.5em 0.6em 0.6em; border: 1px solid rgba(127,127,127,0.3); border-radius: 10px; }
    .pvr.early { border-color: #d4af37; }
    .pvh { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.3em 0.8em; margin-bottom: 0.4em; }
    .pvh b { font-size: 1.05em; }
    .pvh span { font-size: 0.82em; opacity: 0.75; }
    .pv { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5em; }
    .pv .pvc { text-align: center; border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.4em 0.2em; background: rgba(127,127,127,0.06); min-width: 0; }
    .pv .pvc > b { display: block; font-size: 1.6em; line-height: 1.15; }
    .pv small { display: block; opacity: 0.7; font-size: 0.75em; }
    .pv small.lab { opacity: 1; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #ff9a5c; }
    .pv .rate { display: flex; flex-direction: column; gap: 0.1em; margin: 0.3em 0; font-size: 0.85em; }
    .pv .rate span { white-space: nowrap; }
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
    .moretrades { text-align: center; margin: 0.8em 0; }
    .moretrades button { padding: 0.35em 0.8em; font-size: 0.95em; margin: 0 0.2em; }
</style>
