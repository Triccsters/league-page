<script>
    import { onMount } from 'svelte';
    import { currentPairs, nameOf, currentManagers, generated, site, hasYahoo } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import RivalryHub from '$lib/Charts/RivalryHub.svelte';

    const pairs = currentPairs();
    let who = '';
    let ready = false;
    // /rivalries?who=<sleeper handle> opens pre-filtered (used by the manager pages)
    onMount(() => {
        ready = true;
        const w = new URLSearchParams(window.location.search).get('who');
        if (w && currentManagers.includes(w)) who = w;
    });
    $: shown = who ? pairs.filter(p => p.x === who || p.y === who) : pairs;
    const people = [...currentManagers].sort((a, b) => nameOf(a).localeCompare(nameOf(b)));
    // the whole league at a glance: each row's record against each column
    let view = 'matrix';
    const cell = {};
    for (const p of pairs) {
        cell[p.x + '|' + p.y] = { w: p.all.x, l: p.all.y, slug: p.slug };
        cell[p.y + '|' + p.x] = { w: p.all.y, l: p.all.x, slug: p.slug };
    }
    const total = (h) => people.reduce((a, o) => { const c = cell[h + '|' + o]; return c ? [a[0] + c.w, a[1] + c.l] : a; }, [0, 0]);
</script>

<svelte:head><title>Rivalries | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>Rivalries</h1>
    <p class="sub">Every head-to-head since {site.first_season}{hasYahoo ? ', Yahoo and Sleeper eras combined' : ''}. Playoff and consolation games included.</p>

    {#if !who}<RivalryHub />{/if}

    <h2 class="allh">Every series</h2>
    <label class="pick">Show one manager:
        <select bind:value={who}>
            <option value="">Everyone ({pairs.length} rivalries)</option>
            {#each people as p}<option value={p}>{nameOf(p)}</option>{/each}
        </select>
        {#if ready && $myTeam && who !== $myTeam}<button on:click={() => (who = $myTeam)}>Show mine</button>{/if}
    </label>

    <div class="views"><button class:on={view === 'matrix'} on:click={() => (view = 'matrix')}>Grid</button><button class:on={view === 'cards'} on:click={() => (view = 'cards')}>Cards</button></div>

    {#if view === 'matrix' && !who}
    <p class="sub small">Read across: each row is that manager's record against the manager at the top of the column. Tap a square for the full rivalry.</p>
    <div class="mx"><table>
        <thead><tr><th></th>{#each people as c}<th title={nameOf(c)}>{nameOf(c).slice(0, 6)}</th>{/each}<th>All</th></tr></thead>
        <tbody>
            {#each people as r}
                {@const t = total(r)}
                <tr class:mine={ready && r === $myTeam}><th>{nameOf(r)}</th>
                    {#each people as c}
                        {@const x = cell[r + '|' + c]}
                        {#if r === c}<td class="self">·</td>{:else if x}<td class:up={x.w > x.l} class:down={x.w < x.l}><a href="/rivalries/{x.slug}">{x.w}-{x.l}</a></td>{:else}<td class="self">-</td>{/if}
                    {/each}
                    <td class="tot">{t[0]}-{t[1]}</td></tr>
            {/each}
        </tbody>
    </table></div>
    {:else}
    <div class="grid">
        {#each shown as p}
            <a class="card" class:mine={ready && (p.x === $myTeam || p.y === $myTeam)} href="/rivalries/{p.slug}">
                <div class="names">
                    <span class:lead={p.all.x > p.all.y}>{nameOf(p.x)}</span>
                    <span class="vs">vs</span>
                    <span class:lead={p.all.y > p.all.x}>{nameOf(p.y)}</span>
                </div>
                <div class="score">{p.all.x}–{p.all.y}{p.all.t ? `–${p.all.t}` : ''}</div>
                <div class="meta">
                    {p.games} meetings{p.finals ? ` · ${p.finals} final${p.finals > 1 ? 's' : ''}` : ''}
                    {#if p.streak && p.streak.n >= 2} · {nameOf(p.streak.who)} has won {p.streak.n} straight{/if}
                </div>
            </a>
        {/each}
    </div>
    {/if}
    <p class="stamp">Data updated {generated.slice(0, 10)}. Includes {site.season} games played so far.</p>
</div>

<style>
    .holder { max-width: 1000px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub, .stamp { text-align: center; opacity: 0.7; }
    .pick { display: block; text-align: center; margin: 1em 0 1.5em; }
    select { margin-left: 0.5em; padding: 0.3em; font-size: 1em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.8em; }
    .card { display: block; padding: 0.9em 1em; border: 1px solid rgba(127,127,127,0.35); border-radius: 8px; text-decoration: none; color: inherit; }
    .card:hover { border-color: #3498db; }
    .card.mine { border-color: #27ae60; box-shadow: inset 3px 0 0 #27ae60; }
    button { margin-left: 0.5em; padding: 0.3em 0.6em; font-size: 0.95em; }
    .names { display: flex; justify-content: space-between; gap: 0.4em; font-weight: 600; }
    .vs { opacity: 0.5; font-weight: 400; }
    .lead { color: #27ae60; }
    .score { font-size: 1.6em; font-weight: 700; text-align: center; margin: 0.2em 0; font-variant-numeric: tabular-nums; }
    .meta { font-size: 0.85em; opacity: 0.75; text-align: center; }
    .views { display: flex; justify-content: center; gap: 0.4em; margin-bottom: 1em; }
    .views button { margin: 0; border: 1px solid rgba(127,127,127,0.5); background: transparent; color: inherit; border-radius: 16px; padding: 0.3em 1em; font-weight: 700; cursor: pointer; }
    .views button.on { background: #3498db; border-color: #3498db; color: #fff; }
    .small { font-size: 0.88em; }
    .mx { overflow-x: auto; }
    .mx table { border-collapse: collapse; margin: 0 auto; }
    .mx th, .mx td { padding: 0.4em 0.5em; border: 1px solid rgba(127,127,127,0.25); text-align: center; font-size: 0.86em; white-space: nowrap; font-variant-numeric: tabular-nums; }
    .mx tbody th { text-align: left; }
    .mx td a { color: #fff; text-decoration: none; display: block; }
    .mx td.up { background: #1e8449; }
    .mx td.down { background: #a93226; }
    .mx td:not(.up):not(.down) a { color: inherit; }
    .mx td.self { opacity: 0.4; }
    .mx td.tot { font-weight: 700; }
    .mx tr.mine th { box-shadow: inset 3px 0 0 #27ae60; }
</style>
