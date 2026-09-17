<script>
    import { onMount } from 'svelte';
    import { nameOf, managerLink, teamName, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let data = null, error = '', ready = false;
    let q = '', pos = 'All', who = '', open = null;
    onMount(async () => {
        ready = true;
        try { data = await fetch('/data/players.json').then(r => r.json()); }
        catch (e) { error = 'Could not load player history.'; }
    });

    const POS = ['All', 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
    $: people = data ? [...new Set(data.players.flatMap(p => p.s.map(x => x[1])))].sort((a, b) => nameOf(a).localeCompare(nameOf(b))) : [];
    // points for one manager when filtered
    const forWho = (p, h) => p.s.filter(x => x[1] === h).reduce((t, x) => ({ pts: t.pts + x[2], st: t.st + x[3], wk: t.wk + x[4] }), { pts: 0, st: 0, wk: 0 });
    $: list = !data ? [] : data.players
        .filter(p => (pos === 'All' || p.p === pos) && (!q || p.n.toLowerCase().includes(q.toLowerCase())))
        .map(p => who ? { ...p, view: forWho(p, who) } : { ...p, view: { pts: p.pts, st: p.st, wk: p.wk } })
        .filter(p => p.view.wk > 0)
        .sort((a, b) => b.view.pts - a.view.pts)
        .slice(0, q ? 60 : 50);
    const owners = (p) => {
        const m = {};
        for (const [, h, pts] of p.s) m[h] = (m[h] || 0) + pts;
        return Object.entries(m).sort((a, b) => b[1] - a[1]);
    };
    const r1 = (x) => Math.round(x * 10) / 10;
</script>

<div class="holder">
    <h1>Player History</h1>
    <p class="sub">Every player who has been on a {site.league_name} roster since {data?.first_season ?? site.first_season}: who had him, and how many points he scored for them in a starting lineup. Tap a player for his full history.</p>

    {#if data}
        <div class="filters">
            <input type="search" placeholder="Search a player…" bind:value={q} />
            <select bind:value={who}>
                <option value="">All managers</option>
                {#each people as p}<option value={p}>{nameOf(p)}</option>{/each}
            </select>
            {#if ready && $myTeam && who !== $myTeam}<button on:click={() => (who = $myTeam)}>My players</button>{/if}
        </div>
        <div class="pos">{#each POS as p}<button class:on={pos === p} on:click={() => (pos = p)}>{p}</button>{/each}</div>
        <p class="note">{who ? `${nameOf(who)}'s` : 'The league\'s'} top {list.length} by points scored while started{q ? ` matching "${q}"` : ''}.</p>

        <div class="list">
            {#each list as p, i (p.k)}
                <div class="row" class:open={open === p.k}>
                    <button class="line" on:click={() => (open = open === p.k ? null : p.k)}>
                        <span class="rk">{i + 1}</span>
                        <span class="nm"><b>{p.n}</b> <small>{p.p}</small></span>
                        <span class="val">{r1(p.view.pts)}</span>
                        <span class="meta">{p.view.st} starts · {p.view.wk} weeks rostered</span>
                    </button>
                    {#if open === p.k}
                        <div class="detail">
                            <p><b>Scored the most for:</b> {owners(p).slice(0, 3).map(([h, v]) => `${nameOf(h)} (${r1(v)})`).join(', ')}</p>
                            <table>
                                <thead><tr><th>Season</th><th>Manager</th><th class="num">Points started</th><th class="num">Starts</th><th class="num">Weeks rostered</th></tr></thead>
                                <tbody>
                                    {#each p.s as [s, h, pts, st, wk]}
                                        <tr class:mine={ready && h === $myTeam}>
                                            <td>{s}</td>
                                            <td>{#if managerLink(h)}<a href={managerLink(h)}>{nameOf(h)}</a>{:else}{nameOf(h)}{/if}
                                                {#if teamName(s, h) && teamName(s, h) !== nameOf(h)}<small>{teamName(s, h)}</small>{/if}</td>
                                            <td class="num">{r1(pts)}</td><td class="num">{st}</td><td class="num">{wk}</td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>

        <h2>Biggest single games</h2>
        <div class="list">
            {#each data.top_games.slice(0, 15) as g, i}
                <div class="game"><span class="rk">{i + 1}</span><b>{g.n}</b> <small>{g.p}</small><span class="val">{g.pts}</span><span class="meta">{g.season} week {g.week} for {nameOf(g.h)}</span></div>
            {/each}
        </div>
    {:else if error}
        <p class="sub">{error}</p>
    {:else}
        <p class="sub">Loading players…</p>
    {/if}
</div>

<style>
    .holder { max-width: 860px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .filters { display: flex; gap: 0.5em; justify-content: center; flex-wrap: wrap; margin-top: 1em; }
    input, select, .filters button { padding: 0.4em 0.6em; font-size: 1em; }
    input { min-width: 220px; }
    .pos { display: flex; gap: 0.3em; justify-content: center; flex-wrap: wrap; margin: 0.6em 0; }
    .pos button { background: transparent; color: inherit; border: 1px solid rgba(127,127,127,0.45); border-radius: 14px; padding: 0.15em 0.8em; cursor: pointer; }
    .pos button.on { background: #3498db; border-color: #3498db; color: #fff; }
    .row { border-bottom: 1px solid rgba(127,127,127,0.2); }
    .row.open { background: rgba(52, 152, 219, 0.08); }
    .line { all: unset; box-sizing: border-box; width: 100%; cursor: pointer; display: grid; grid-template-columns: 2em 1fr auto 13em; gap: 0.6em; align-items: center; padding: 0.4em 0.3em; font-size: 0.92em; }
    .game { display: grid; grid-template-columns: 2em auto 1fr auto 11em; gap: 0.5em; align-items: center; padding: 0.35em 0.3em; border-bottom: 1px solid rgba(127,127,127,0.2); font-size: 0.9em; }
    .rk { opacity: 0.55; text-align: right; }
    small { opacity: 0.65; }
    .val { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
    .meta { font-size: 0.8em; opacity: 0.7; text-align: right; }
    .detail { padding: 0.2em 0.8em 0.8em 2.6em; font-size: 0.88em; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.3em 0.4em; border-bottom: 1px solid rgba(127,127,127,0.18); text-align: left; white-space: nowrap; }
    td small { margin-left: 0.3em; font-style: italic; }
    td a { color: inherit; font-weight: 600; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; }
    @media (max-width: 560px) { .line { grid-template-columns: 1.6em 1fr auto; } .line .meta { grid-column: 2 / span 2; text-align: left; } }
</style>
