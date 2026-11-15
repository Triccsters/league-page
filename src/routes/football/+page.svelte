<script>
    // Real football numbers from each manager's starters (T.J., 2026-11-13).
    import { onMount } from 'svelte';
    import { nameOf, managerLink, site, currentManagers } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import { playerImg, hideBroken, avatarOf } from '$lib/utils/avatars';

    let data = null, error = '', ready = false;
    let season = 'all', sortKey = 'yds', sortDir = -1, everyone = false;
    onMount(async () => {
        ready = true;
        try { data = await fetch('/data/football.json').then(r => r.json()); }
        catch (e) { error = 'Could not load the football stats.'; }
    });

    const COLS = [['pass_yd', 'Pass yds'], ['pass_td', 'Pass TD'], ['pass_int', 'INT'], ['rush_yd', 'Rush yds'], ['rush_td', 'Rush TD'],
                  ['rec', 'Catches'], ['rec_yd', 'Rec yds'], ['rec_td', 'Rec TD'], ['yds', 'Total yds'], ['td', 'Total TD'], ['fgm', 'FG']];
    const GAMES = [['pass_yd', 'Passing yards'], ['rush_yd', 'Rushing yards'], ['rec_yd', 'Receiving yards'], ['rec', 'Catches'], ['td', 'Touchdowns']];
    const PLAYS = [['pass_lng', 'Longest pass'], ['rush_lng', 'Longest run'], ['rec_lng', 'Longest catch'], ['fgm_lng', 'Longest field goal']];
    const fmt = (n) => Math.round(n).toLocaleString('en-US');
    const full = (r) => r ? { ...r, yds: r.pass_yd + r.rush_yd + r.rec_yd, td: r.pass_td + r.rush_td + r.rec_td } : null;
    $: hasK = data ? Object.values(data.managers).some(m => m.tot.fgm > 0) : false;
    $: cols = COLS.filter(c => c[0] !== 'fgm' || hasK);
    $: plays = PLAYS.filter(c => c[0] !== 'fgm_lng' || hasK);
    $: seasons = data ? [...data.seasons].sort((a, b) => b - a) : [];
    $: rows = !data ? [] : Object.entries(data.managers)
        .map(([h, m]) => ({ h, v: full(season === 'all' ? m.tot : m.seasons[season]) }))
        .filter(r => r.v && (everyone || season !== 'all' || currentManagers.includes(r.h)))
        .sort((a, b) => sortDir * (a.v[sortKey] - b.v[sortKey]));
    $: former = data ? Object.keys(data.managers).filter(h => !currentManagers.includes(h)).length : 0;
    $: best = Object.fromEntries(cols.map(([k]) => [k, rows.length ? Math.max(...rows.map(r => r.v[k])) : 0]));
    const sortBy = (k) => { if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = -1; } };
    const arrow = (k, sk, sd) => (sk === k ? (sd < 0 ? ' ▼' : ' ▲') : '');
    // game and play rows: [value, player, pos, id, manager, season, week]
    const pic = (g) => playerImg({ id: g[3], pos: g[2] });
</script>

<div class="holder">
    <h1>Football Stats</h1>
    {#if data}
        <p class="sub">The real football behind the fantasy points: yards, catches and touchdowns from the players each manager had in a starting lineup. {site.league_name} on Sleeper, {data.seasons[0]} to {data.through[0]} week {data.through[1]}, playoffs included.</p>

        <section>
            <p class="eyebrow">By manager</p>
            <h2>{season === 'all' ? 'Career totals' : season + ' season'}</h2>
            <div class="pick">
                <button class:on={season === 'all'} on:click={() => (season = 'all')}>All seasons</button>
                {#each seasons as s}<button class:on={season === String(s)} on:click={() => (season = String(s))}>{s}</button>{/each}
            </div>
            <div class="scroll">
                <table>
                    <thead><tr>
                        <th class="rk">#</th><th>Manager</th>
                        {#each cols as [k, label]}<th class="num"><button class="th" on:click={() => sortBy(k)}>{label}{arrow(k, sortKey, sortDir)}</button></th>{/each}
                    </tr></thead>
                    <tbody>
                        {#each rows as r, i (r.h)}
                            <tr class:mine={ready && r.h === $myTeam}>
                                <td class="rk">{i + 1}</td>
                                <td class="who">{#if avatarOf(r.h)}<img src={avatarOf(r.h)} alt="" loading="lazy" on:error={hideBroken} />{/if}{#if managerLink(r.h)}<a href={managerLink(r.h)}>{nameOf(r.h)}</a>{:else}{nameOf(r.h)}{/if}</td>
                                {#each cols as [k]}<td class="num" class:top={k !== 'pass_int' && r.v[k] === best[k] && best[k] > 0}>{fmt(r.v[k])}</td>{/each}
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
            <p class="fine">Tap a column to sort. The highest number in each column is in orange, interceptions aside.{#if season === 'all' && former}{' '}{#if everyone}<button class="link" on:click={() => (everyone = false)}>Hide former managers</button>{:else}<button class="link" on:click={() => (everyone = true)}>Show {former} former manager{former === 1 ? '' : 's'}</button>{/if}{/if}</p>
        </section>

        <section>
            <p class="eyebrow">Single games</p>
            <h2>Biggest days in a lineup</h2>
            <div class="cards">
                {#each GAMES as [k, label]}
                    <div class="card">
                        <h3>{label}</h3>
                        {#each data.games[k].slice(0, 5) as g, i}
                            <div class="row" class:lead={i === 0}>
                                <span class="pic">{#if pic(g)}<img src={pic(g)} alt="" loading="lazy" on:error={hideBroken} />{/if}</span>
                                <span class="txt"><b>{g[1]}</b><small>{g[5]} week {g[6]} for {nameOf(g[4])}</small></span>
                                <span class="v">{fmt(g[0])}</span>
                            </div>
                        {/each}
                    </div>
                {/each}
            </div>
        </section>

        <section>
            <p class="eyebrow">Single plays</p>
            <h2>Longest plays in a lineup</h2>
            <div class="cards">
                {#each plays as [k, label]}
                    <div class="card">
                        <h3>{label}</h3>
                        {#each data.plays[k].slice(0, 5) as g, i}
                            <div class="row" class:lead={i === 0}>
                                <span class="pic">{#if pic(g)}<img src={pic(g)} alt="" loading="lazy" on:error={hideBroken} />{/if}</span>
                                <span class="txt"><b>{g[1]}</b><small>{g[5]} week {g[6]} for {nameOf(g[4])}</small></span>
                                <span class="v">{fmt(g[0])}<small> yds</small></span>
                            </div>
                        {/each}
                    </div>
                {/each}
            </div>
            <p class="fine">Only weeks played on Sleeper are counted, because that is where the play-by-play numbers come from.</p>
        </section>
    {:else if error}
        <p class="sub">{error}</p>
    {:else}
        <p class="sub">Loading the football stats…</p>
    {/if}
</div>

<style>
    .holder { max-width: 1100px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin: 0.1em 0 0.5em; font-size: 1.35em; }
    section { margin-top: 2.2em; }
    .sub { text-align: center; opacity: 0.8; font-size: 0.92em; line-height: 1.5; max-width: 50em; margin: 0 auto; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    .pick { display: flex; gap: 0.3em; flex-wrap: wrap; margin: 0.4em 0 0.8em; }
    .pick button { background: transparent; color: inherit; border: 1px solid rgba(127,127,127,0.45); border-radius: 14px; padding: 0.15em 0.8em; cursor: pointer; }
    .pick button.on { background: #3498db; border-color: #3498db; color: #fff; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.18); text-align: left; white-space: nowrap; }
    .th { all: unset; cursor: pointer; font-weight: 700; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .rk { opacity: 0.55; text-align: right; width: 2em; }
    .who { display: flex; align-items: center; gap: 0.45em; font-weight: 600; }
    .who img { width: 26px; height: 26px; border-radius: 50%; object-fit: cover; }
    .who a { color: inherit; }
    td.top { color: #ff9a5c; font-weight: 800; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .fine { font-size: 0.8em; opacity: 0.7; margin-top: 0.7em; }
    .link { all: unset; cursor: pointer; text-decoration: underline; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 0.8em; }
    .card { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 16px; padding: 0.9em 1em 0.6em; min-width: 0; }
    h3 { margin: 0 0 0.5em; font-size: 0.82em; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #9fb0cc; }
    .row { display: grid; grid-template-columns: 34px 1fr auto; gap: 0.6em; align-items: center; padding: 0.4em 0; border-top: 1px solid #25304a; }
    .row.lead { border-top: none; border-left: 3px solid #ff7a2f; padding-left: 0.6em; }
    .pic { width: 34px; height: 34px; border-radius: 50%; overflow: hidden; background: #0b101c; display: inline-block; }
    .pic img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .txt { min-width: 0; display: flex; flex-direction: column; }
    .txt b { color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .txt small { color: #9fb0cc; font-size: 0.78em; }
    .v { font-weight: 800; font-size: 1.15em; color: #fff; font-variant-numeric: tabular-nums; }
    .row.lead .v { font-size: 1.5em; }
    .v small { font-size: 0.55em; color: #9fb0cc; font-weight: 600; }
</style>
