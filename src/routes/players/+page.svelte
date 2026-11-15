<script>
    import { onMount } from 'svelte';
    import { nameOf, managerLink, teamName, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import { playerImg, hideBroken } from '$lib/utils/avatars';

    let data = null, hof = null, error = '', ready = false;
    let q = '', pos = 'All', who = '', open = null;
    let sortKey = 'pts', sortDir = -1, shown = 50, allNear = false;
    onMount(async () => {
        ready = true;
        try { data = await fetch('/data/players.json').then(r => r.json()); }
        catch (e) { error = 'Could not load player history.'; }
        try { hof = await fetch('/data/player_hof.json').then(r => r.json()); } catch (e) { hof = null; }
        const w = new URLSearchParams(location.search).get('who');
        if (w) who = w;
    });

    const POS = ['All', 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
    const ROUTE = { peak: 'Peak', champion: 'Champion', best: 'Best at the position' };
    const r1 = (x) => Math.round(x * 10) / 10;
    const img = (p) => playerImg({ id: p.id, pos: p.p });
    $: hasPos = data ? new Set(data.players.map(p => p.p)) : new Set();
    $: people = data ? [...new Set(data.players.flatMap(p => p.s.map(x => x[1])))].sort((a, b) => nameOf(a).localeCompare(nameOf(b))) : [];
    $: inHall = new Set((hof?.inductees || []).map(c => c.k));
    $: benchFrom = data?.bench_from || 0;

    // one manager's share of a player when the list is filtered
    const forWho = (p, h) => p.s.filter(x => x[1] === h).reduce((t, x) => ({ pts: t.pts + x[2], st: t.st + x[3], wk: t.wk + x[4], b: t.b + (x[5] || 0) }), { pts: 0, st: 0, wk: 0, b: 0 });
    const shape = (p, v) => ({ ...p, v: { ...v, per: v.st ? v.pts / v.st : 0, yrs: new Set(p.s.map(x => x[0])).size, first: Math.min(...p.s.map(x => x[0])) } });
    $: rows = !data ? [] : data.players
        .filter(p => (pos === 'All' || p.p === pos) && (!q || p.n.toLowerCase().includes(q.toLowerCase())))
        .map(p => shape(p, who ? forWho(p, who) : { pts: p.pts, st: p.st, wk: p.wk, b: p.b || 0 }))
        .filter(p => p.v.wk > 0)
        .sort((a, b) => sortKey === 'n' ? sortDir * a.n.localeCompare(b.n) : sortDir * (a.v[sortKey] - b.v[sortKey]) || b.v.pts - a.v.pts);
    $: list = rows.slice(0, shown);
    const sortBy = (k) => { if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = k === 'n' || k === 'first' ? 1 : -1; } shown = 50; };
    const arrow = (k, sk, sd) => (sk === k ? (sd < 0 ? ' ▼' : ' ▲') : '');
    const owners = (p) => {
        const m = {};
        for (const [, h, pts] of p.s) m[h] = (m[h] || 0) + pts;
        return Object.entries(m).sort((a, b) => b[1] - a[1]);
    };
    const COLS = [['st', 'Starts'], ['pts', 'Points'], ['per', 'Per start'], ['b', 'Bench pts'], ['yrs', 'Seasons'], ['first', 'First']];
</script>

<div class="holder">
    <h1>Players</h1>
    <p class="sub">Every player who has been on a {site.league_name} roster since {data?.first_season ?? site.first_season}, the ones who made the Hall of Fame, and the ones whose best years went to waste here.</p>
    <p class="jump"><a href="#hall">Hall of Fame</a><a href="#wasted">Prime years wasted</a><a href="#all">Every player</a><a href="#games">Biggest games</a></p>

    {#if hof && hof.inductees.length}
        <section id="hall">
            <p class="eyebrow">Player Hall of Fame</p>
            <h2>{hof.inductees.length} players, three ways in</h2>
            <p class="lede">An <b>All-League season</b> is a top {hof.rules.top.QB} finish at quarterback or tight end, or top {hof.rules.top.RB} at running back or receiver{#if hasPos.has('K') || hasPos.has('DEF')}, or first among kickers or defences{/if}, in points scored in a {site.league_name} lineup, with at least {hof.rules.min_starts} starts. A <b>ring</b> is {hof.rules.ring_starts} or more starts that season for the team that won the title.</p>
            <div class="rules">
                <div class="rule"><span>Peak</span><b>{hof.rules.peak}</b><p>All-League seasons</p></div>
                <div class="rule"><span>Champion</span><b>{hof.rules.rings} + {hof.rules.champ_al}</b><p>{hof.rules.rings} rings and {hof.rules.champ_al} All-League seasons</p></div>
                <div class="rule"><span>Best at the position</span><b>{hof.rules.best}</b><p>seasons finishing first at the position</p></div>
            </div>
            <div class="cards">
                {#each hof.inductees as c (c.k)}
                    <div class="card">
                        <div class="top">
                            {#if img(c)}<img class="face" class:logo={c.p === 'DEF'} src={img(c)} alt="" loading="lazy" on:error={hideBroken} />{/if}
                            <div>
                                <b class="name">{c.n}</b>
                                <div class="tags"><span class="chip {c.p}">{c.p}</span>{#each c.via as v}<span class="via">{ROUTE[v]}</span>{/each}</div>
                            </div>
                        </div>
                        <div class="big"><div><b>{c.al.length}</b><span>All-League</span></div><div><b>{c.no1.length}</b><span>Times first</span></div><div><b>{c.rings.length}</b><span>Rings</span></div><div><b>{c.st}</b><span>Starts</span></div></div>
                        <p class="yrs"><span>All-League</span> {#each c.al as y, i}{i ? ', ' : ''}<em class:first={c.no1.includes(y)}>{y}</em>{/each}</p>
                        <p class="yrs"><span>Rings</span> {c.rings.length ? c.rings.join(', ') : 'None'}</p>
                        <p class="yrs"><span>Here</span> {c.first} to {c.last}, {c.mgrs} manager{c.mgrs === 1 ? '' : 's'}. Most points for {nameOf(c.top).replace(/\.$/, '')}.</p>
                    </div>
                {/each}
            </div>
            <p class="fine">A year in orange is a first-place finish at the position. {#if hof.missing.length}{hof.missing.join(' and ')} {hof.missing.length === 1 ? 'is' : 'are'} missing from the records, so nothing from {hof.missing.length === 1 ? 'that season' : 'those seasons'} counts.{/if} The current season counts once it is over.</p>
            {#if hof.near.length}
                <p class="near"><b>One season short:</b> {(allNear ? hof.near : hof.near.slice(0, 8)).map(c => `${c.n} (${c.al.length})`).join(', ')}{#if hof.near.length > 8 && !allNear} <button class="link" on:click={() => (allNear = true)}>and {hof.near.length - 8} more</button>{/if}</p>
            {/if}
        </section>

        {#if hof.wasted.length}
            <section id="wasted">
                <p class="eyebrow">Prime years wasted</p>
                <h2>Great players, wrong place</h2>
                <p class="lede">Players who were difference makers, top of their position on every point they scored that year, but spent at least {hof.rules.waste_seasons} of those seasons and at least half of them on a losing team that missed the playoffs, or sitting on a bench.</p>
                <div class="cards">
                    {#each hof.wasted as w (w.k)}
                        <div class="card waste">
                            <div class="top">
                                {#if img(w)}<img class="face" src={img(w)} alt="" loading="lazy" on:error={hideBroken} />{/if}
                                <div>
                                    <b class="name">{w.n}</b>
                                    <div class="tags"><span class="chip {w.p}">{w.p}</span><span class="via">{w.seasons.length} of {w.prime} prime seasons</span></div>
                                </div>
                            </div>
                            {#each w.seasons as s}
                                <p class="lost"><b>{s.season}</b> {w.p}{s.rank} for {nameOf(s.h)}{#if s.loser}, who went {s.w}-{s.l} and missed the playoffs{/if}{#if s.benched}{s.loser ? '. He also sat' : ', but sat'} {s.bw} weeks and scored {Math.round(s.bench)} points on the bench{/if}.</p>
                            {/each}
                            <p class="yrs"><span>Rings here</span> {w.rings || 'None'}</p>
                        </div>
                    {/each}
                </div>
                {#if hof.bench_from > hof.first_season}<p class="fine">Bench points are on record from {hof.bench_from}. Before that only losing teams can be counted.</p>{/if}
            </section>
        {/if}
    {/if}

    {#if data}
        <section id="all">
            <p class="eyebrow">Every player</p>
            <h2>Player history</h2>
            <div class="filters">
                <input type="search" placeholder="Search a player…" bind:value={q} />
                <select bind:value={who}>
                    <option value="">All managers</option>
                    {#each people as p}<option value={p}>{nameOf(p)}</option>{/each}
                </select>
                {#if ready && $myTeam && who !== $myTeam}<button on:click={() => (who = $myTeam)}>My players</button>{/if}
            </div>
            <div class="pos">{#each POS.filter(p => p === 'All' || hasPos.has(p)) as p}<button class:on={pos === p} on:click={() => { pos = p; shown = 50; }}>{p}</button>{/each}</div>
            <p class="note">{rows.length} player{rows.length === 1 ? '' : 's'}{who ? ` for ${nameOf(who)}` : ''}{q ? ` matching "${q}"` : ''}. Tap a column to sort, tap a player for his full history.</p>

            <div class="scroll">
                <table class="all">
                    <thead><tr>
                        <th class="rk">#</th>
                        <th><button class="th" on:click={() => sortBy('n')}>Player{arrow('n', sortKey, sortDir)}</button></th>
                        {#each COLS as [k, label]}<th class="num c-{k}"><button class="th" on:click={() => sortBy(k)}>{label}{arrow(k, sortKey, sortDir)}</button></th>{/each}
                    </tr></thead>
                    <tbody>
                        {#each list as p, i (p.k)}
                            <tr class="line" class:open={open === p.k} on:click={() => (open = open === p.k ? null : p.k)}>
                                <td class="rk">{i + 1}</td>
                                <td class="who">
                                    <span class="pic">{#if img(p)}<img class:logo={p.p === 'DEF'} src={img(p)} alt="" loading="lazy" on:error={hideBroken} />{/if}</span>
                                    <b>{p.n}</b><span class="chip {p.p}">{p.p}</span>{#if inHall.has(p.k)}<span class="hof" title="Hall of Fame">HOF</span>{/if}
                                </td>
                                <td class="num c-st">{p.v.st}</td>
                                <td class="num c-pts"><b>{r1(p.v.pts)}</b></td>
                                <td class="num c-per">{r1(p.v.per)}</td>
                                <td class="num c-b">{p.v.first >= benchFrom || p.v.b ? r1(p.v.b) : ''}</td>
                                <td class="num c-yrs">{p.v.yrs}</td>
                                <td class="num c-first">{p.v.first}</td>
                            </tr>
                            {#if open === p.k}
                                <tr class="detail"><td colspan="8">
                                    <p><b>Scored the most for:</b> {owners(p).slice(0, 3).map(([h, v]) => `${nameOf(h)} (${r1(v)})`).join(', ')}</p>
                                    <table>
                                        <thead><tr><th>Season</th><th>Manager</th><th class="num">Points started</th><th class="num">Starts</th><th class="num">Weeks rostered</th><th class="num">Bench points</th></tr></thead>
                                        <tbody>
                                            {#each p.s as [s, h, pts, st, wk, bn]}
                                                <tr class:mine={ready && h === $myTeam}>
                                                    <td>{s}</td>
                                                    <td>{#if managerLink(h)}<a href={managerLink(h)}>{nameOf(h)}</a>{:else}{nameOf(h)}{/if}
                                                        {#if teamName(s, h) && teamName(s, h) !== nameOf(h)}<small>{teamName(s, h)}</small>{/if}</td>
                                                    <td class="num">{r1(pts)}</td><td class="num">{st}</td><td class="num">{wk}</td><td class="num">{s >= benchFrom ? r1(bn || 0) : ''}</td>
                                                </tr>
                                            {/each}
                                        </tbody>
                                    </table>
                                </td></tr>
                            {/if}
                        {/each}
                    </tbody>
                </table>
            </div>
            {#if rows.length > shown}<p class="more"><button on:click={() => (shown += 50)}>Show 50 more</button></p>{/if}
        </section>

        <section id="games">
            <p class="eyebrow">Single games</p>
            <h2>Biggest single games</h2>
            <div class="list">
                {#each data.top_games.slice(0, 15) as g, i}
                    <div class="game"><span class="rk">{i + 1}</span><b>{g.n}</b> <small>{g.p}</small><span class="val">{g.pts}</span><span class="meta">{g.season} week {g.week} for {nameOf(g.h)}</span></div>
                {/each}
            </div>
        </section>
    {:else if error}
        <p class="sub">{error}</p>
    {:else}
        <p class="sub">Loading players…</p>
    {/if}
</div>

<style>
    .holder { max-width: 1040px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin: 0.1em 0 0.5em; font-size: 1.35em; }
    section { margin-top: 2.2em; scroll-margin-top: 5em; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .jump { display: flex; gap: 0.5em; justify-content: center; flex-wrap: wrap; margin: 0.8em 0 0; }
    .jump a { border: 1px solid rgba(127,127,127,0.45); border-radius: 14px; padding: 0.2em 0.9em; font-size: 0.85em; color: inherit; text-decoration: none; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    .lede { font-size: 0.93em; line-height: 1.55; opacity: 0.88; max-width: 52em; }
    .rules { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8em; margin: 1em 0; }
    .rule { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-top: 3px solid #ff7a2f; border-radius: 14px; padding: 0.8em 1em; }
    .rule span { font-size: 0.72em; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; color: #9fb0cc; }
    .rule b { display: block; font-size: 2em; line-height: 1.15; color: #fff; }
    .rule p { margin: 0; font-size: 0.85em; color: #c6d2e6; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 0.8em; }
    .card { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 16px; padding: 0.9em 1em; min-width: 0; }
    .card.waste { border-top: 3px solid #8e44ad; }
    .top { display: flex; gap: 0.7em; align-items: center; margin-bottom: 0.6em; }
    .face { width: 58px; height: 58px; border-radius: 50%; object-fit: cover; background: #0b101c; border: 2px solid #25304a; flex: none; }
    .face.logo, .pic img.logo { object-fit: contain; }
    .name { font-size: 1.1em; color: #fff; }
    .tags { display: flex; gap: 0.3em; flex-wrap: wrap; margin-top: 0.25em; }
    .chip { font-size: 0.68em; font-weight: 800; border-radius: 6px; padding: 0.1em 0.45em; color: #fff; background: #566573; letter-spacing: 0.04em; }
    .chip.QB { background: #c0392b; } .chip.RB { background: #1e8449; } .chip.WR { background: #2471a3; }
    .chip.TE { background: #b9770e; } .chip.K { background: #7d3c98; } .chip.DEF { background: #566573; }
    .via { font-size: 0.68em; font-weight: 700; border-radius: 6px; padding: 0.1em 0.45em; color: #ffd9c2; border: 1px solid #ff7a2f; }
    .big { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3em; text-align: center; border-top: 1px solid #25304a; border-bottom: 1px solid #25304a; padding: 0.5em 0; margin-bottom: 0.5em; }
    .big b { display: block; font-size: 1.45em; color: #fff; line-height: 1.1; font-variant-numeric: tabular-nums; }
    .big span { font-size: 0.66em; text-transform: uppercase; letter-spacing: 0.06em; color: #9fb0cc; }
    .yrs { margin: 0.25em 0; font-size: 0.84em; line-height: 1.45; color: #c6d2e6; }
    .yrs span { display: inline-block; min-width: 5.6em; font-size: 0.82em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #9fb0cc; }
    .yrs em { font-style: normal; }
    .yrs em.first { color: #ff9a5c; font-weight: 800; }
    .lost { margin: 0.35em 0; font-size: 0.86em; line-height: 1.45; color: #dbe4f3; }
    .lost b { color: #fff; }
    .fine { font-size: 0.8em; opacity: 0.7; margin-top: 0.8em; }
    .near { font-size: 0.88em; line-height: 1.5; }
    .link { all: unset; cursor: pointer; text-decoration: underline; }
    .filters { display: flex; gap: 0.5em; justify-content: center; flex-wrap: wrap; margin-top: 1em; }
    input, select, .filters button, .more button { padding: 0.4em 0.6em; font-size: 1em; }
    input { min-width: 220px; }
    .pos { display: flex; gap: 0.3em; justify-content: center; flex-wrap: wrap; margin: 0.6em 0; }
    .pos button { background: transparent; color: inherit; border: 1px solid rgba(127,127,127,0.45); border-radius: 14px; padding: 0.15em 0.8em; cursor: pointer; }
    .pos button.on { background: #3498db; border-color: #3498db; color: #fff; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.35em 0.45em; border-bottom: 1px solid rgba(127,127,127,0.18); text-align: left; white-space: nowrap; }
    .all { font-size: 0.92em; }
    .th { all: unset; cursor: pointer; font-weight: 700; }
    tr.line { cursor: pointer; }
    tr.line.open, tr.detail { background: rgba(52, 152, 219, 0.08); }
    .who { display: flex; align-items: center; gap: 0.45em; }
    .pic { width: 34px; height: 34px; border-radius: 50%; overflow: hidden; background: rgba(127,127,127,0.2); flex: none; display: inline-block; }
    .pic img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .hof { font-size: 0.66em; font-weight: 800; color: #1a1205; background: #f1c40f; border-radius: 6px; padding: 0.1em 0.4em; }
    .detail td { white-space: normal; padding: 0.4em 0.8em 0.9em 2.6em; font-size: 0.92em; }
    .detail table td, .detail table th { white-space: nowrap; }
    td small { margin-left: 0.3em; font-style: italic; opacity: 0.65; }
    td a { color: inherit; font-weight: 600; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .rk { opacity: 0.55; text-align: right; width: 2em; }
    .more { text-align: center; margin-top: 0.8em; }
    .game { display: grid; grid-template-columns: 2em auto 1fr auto 11em; gap: 0.5em; align-items: center; padding: 0.35em 0.3em; border-bottom: 1px solid rgba(127,127,127,0.2); font-size: 0.9em; }
    small { opacity: 0.65; }
    .val { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
    .meta { font-size: 0.8em; opacity: 0.7; text-align: right; }
    @media (max-width: 720px) {
        .rules { grid-template-columns: 1fr; }
        .c-b, .c-yrs, .c-first { display: none; }
        .detail td { padding-left: 0.6em; }
        .game { grid-template-columns: 1.6em auto 1fr auto; } .game .meta { grid-column: 2 / span 3; text-align: left; }
    }
    @media (max-width: 460px) { .c-per { display: none; } .pic { width: 28px; height: 28px; } }
</style>
