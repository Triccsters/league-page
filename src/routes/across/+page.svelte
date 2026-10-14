<script>
    // Across the leagues: the same people play each other in more than one of the
    // Sleeper leagues. Data: scripts/crossleague.py -> src/lib/data/crossleague.json.
    import { onMount } from 'svelte';
    import { site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    // optional file: League Bound (ESPN) has none
    const files = import.meta.glob('/src/lib/data/crossleague.json', { eager: true, import: 'default' });
    const data = Object.values(files)[0] || {};
    const leagues = data.leagues || [];
    const L = Object.fromEntries(leagues.map(l => [l.i, l]));
    const SHORT = { 'FL Players': 'FLP', 'FL Evolution': 'Evo', 'Lets go Brandon': 'LGB', 'Megalabowl': 'Mega' };
    const short = (i) => SHORT[L[i]?.name] || L[i]?.name || '?';
    const names = Object.fromEntries((data.people || []).map(p => [p.h, p.name]));
    const nm = (h) => names[h] || h;

    let ready = false;
    onMount(() => { ready = true; });

    let since = 0;            // 0 = every year on record; 2019 = the years FL Evolution has existed
    let who = '';
    let open = null;

    const tally = (games) => {
        const t = { x: 0, y: 0, t: 0, by: {} };
        for (const [s, w, i, xp, yp] of games) {
            const b = (t.by[i] ||= { x: 0, y: 0, t: 0 });
            const k = xp > yp ? 'x' : yp > xp ? 'y' : 't';
            t[k]++; b[k]++;
        }
        return t;
    };
    const streakOf = (p, games) => {
        let s = null;
        for (const g of [...games].reverse()) {
            const k = g[3] > g[4] ? p.x : g[4] > g[3] ? p.y : null;
            if (!k) break;
            if (!s) s = { who: k, n: 1 };
            else if (k === s.who) s.n++;
            else break;
        }
        return s;
    };

    $: pairs = (data.pairs || []).map(p => {
        const games = p.games.filter(g => g[0] >= since);
        const lg = [...new Set(games.map(g => g[2]))].sort();
        return { ...p, shown: games, lg, rec: tally(games), streak: streakOf(p, games), last: games[games.length - 1] };
    }).filter(p => p.lg.length > 1 && (!who || p.x === who || p.y === who))
      .sort((a, b) => b.shown.length - a.shown.length || b.lg.length - a.lg.length);

    $: people = (data.people || []).map(p => {
        const per = {};
        let w = 0, l = 0, t = 0;
        // per-league regular-season record against everyone, all years (the year filter
        // only applies to the rivalries table)
        for (const [i, r] of Object.entries(p.record || {})) { per[i] = r; w += r[0]; l += r[1]; t += r[2]; }
        return { ...p, per, w, l, t, pct: (w + t / 2) / Math.max(1, w + l + t) };
    }).sort((a, b) => b.pct - a.pct);

    const pctStr = (x) => `${Math.round(x * 1000) / 10}%`;
    $: me = ready && $myTeam && (data.people || []).some(p => p.h === $myTeam) ? $myTeam : null;
</script>

<svelte:head><title>Across the Leagues | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>Across the Leagues</h1>
    {#if !leagues.length}
        <p class="sub">This league isn't on Sleeper, so nobody here can be matched to the other leagues.</p>
    {:else}
        <p class="sub">
            {(data.people || []).length} people play each other in more than one league. These records add up every game across
            {#each leagues as l, k}<a href={l.site} rel="external">{l.name}</a>{k < leagues.length - 2 ? ', ' : k === leagues.length - 2 ? ' and ' : ''}{/each},
            playoffs included.
        </p>

        <div class="controls">
            <label>Years:
                <select bind:value={since}>
                    <option value={0}>Every year on record</option>
                    <option value={2019}>2019 on (FL Evolution's years)</option>
                    <option value={2022}>2022 on (Lets go Brandon's years)</option>
                </select>
            </label>
            <label>Person:
                <select bind:value={who}>
                    <option value="">Everyone</option>
                    {#each (data.people || []).slice().sort((a, b) => nm(a.h).localeCompare(nm(b.h))) as p}
                        <option value={p.h}>{nm(p.h)}</option>
                    {/each}
                </select>
            </label>
            {#if me && who !== me}
                <button on:click={() => (who = me)}>Show mine</button>
            {/if}
        </div>

        <h2>Rivalries that cross leagues</h2>
        <p class="note">Pairs who have met in two or more leagues, most meetings first. Tap a row for every game.</p>
        <div class="tablewrap">
            <table>
                <thead><tr><th>Rivalry</th><th>Record</th><th class="wide">Games</th><th>By league</th><th class="wide">Streak</th></tr></thead>
                <tbody>
                    {#each pairs as p (p.x + p.y)}
                        <tr class="row" class:mine={me && (p.x === me || p.y === me)} on:click={() => (open = open === p.x + p.y ? null : p.x + p.y)}>
                            <td class="pair">
                                <span class:lead={p.rec.x > p.rec.y}>{nm(p.x)}</span>
                                <span class="vs">vs</span>
                                <span class:lead={p.rec.y > p.rec.x}>{nm(p.y)}</span>
                            </td>
                            <td class="num rec">{p.rec.x}-{p.rec.y}{p.rec.t ? `-${p.rec.t}` : ''}</td>
                            <td class="num wide">{p.shown.length}</td>
                            <td class="split">
                                {#each p.lg as i}
                                    <span class="chip" title={L[i]?.name}>{short(i)} {p.rec.by[i].x}-{p.rec.by[i].y}{p.rec.by[i].t ? `-${p.rec.by[i].t}` : ''}</span>
                                {/each}
                            </td>
                            <td class="streak wide">{#if p.streak && p.streak.n >= 2}{nm(p.streak.who)} {p.streak.n}{:else}-{/if}</td>
                        </tr>
                        {#if open === p.x + p.y}
                            <tr class="games"><td colspan="5">
                                <div class="gl">
                                    {#each [...p.shown].reverse() as g}
                                        <div class="g">
                                            <span class="when">{g[0]} wk {g[1]}</span>
                                            <span class="chip">{short(g[2])}</span>
                                            <span class:won={g[3] > g[4]}>{nm(p.x)} {g[3]}</span>
                                            <span class="vs">-</span>
                                            <span class:won={g[4] > g[3]}>{g[4]} {nm(p.y)}</span>
                                            {#if g[5]}<span class="po">{g[6] || 'Playoffs'}</span>{/if}
                                        </div>
                                    {/each}
                                </div>
                            </td></tr>
                        {/if}
                    {/each}
                </tbody>
            </table>
        </div>
        {#if !pairs.length}<p class="note">No pair has met in two leagues in those years.</p>{/if}

        <h2>Everyone's record in every league</h2>
        <p class="note">Regular-season record against everyone, all years on record, for the people in more than one league. Best combined winning percentage first.</p>
        <div class="tablewrap">
            <table>
                <thead><tr><th>Person</th><th>Combined</th><th>Win %</th>{#each leagues as l}<th title={l.name}>{short(l.i)}</th>{/each}</tr></thead>
                <tbody>
                    {#each people as p (p.h)}
                        <tr class:mine={me === p.h}>
                            <td>{nm(p.h)}{#if p.name}<small class="h">{p.h}</small>{/if}</td>
                            <td class="num">{p.w}-{p.l}{p.t ? `-${p.t}` : ''}</td>
                            <td class="num">{pctStr(p.pct)}</td>
                            {#each leagues as l}
                                <td class="num">{#if p.per[l.i]}{p.per[l.i][0]}-{p.per[l.i][1]}{:else}<span class="dim">-</span>{/if}</td>
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <p class="note key">
            {#each leagues as l, k}{short(l.i)} = {l.name} (since {l.first}){k < leagues.length - 1 ? ' · ' : ''}{/each}
        </p>
        <p class="note">
            Same Sleeper account means same person, including old account names (Austin played as Austin7Rock before RockMNwild).
            Someone on two different accounts won't be joined up. League Bound is on ESPN and isn't included.
            FL Players counts back to 2008, Yahoo years included.
        </p>
        {#if data.generated}<p class="stamp">Data updated {data.generated.slice(0, 10)}.</p>{/if}
    {/if}
</div>

<style>
    .holder { max-width: 1000px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin: 1.4em 0 0.2em; font-size: 1.2em; }
    .sub, .stamp { text-align: center; opacity: 0.75; }
    .sub a { color: #3498db; }
    .controls { display: flex; flex-wrap: wrap; gap: 0.6em 1.2em; justify-content: center; margin: 1em 0; }
    select { margin-left: 0.4em; padding: 0.3em; font-size: 0.95em; max-width: 100%; }
    button { padding: 0.3em 0.6em; font-size: 0.95em; }
    .note { font-size: 0.85em; opacity: 0.75; margin: 0.2em 0 0.6em; }
    .tablewrap { overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; font-size: 0.92em; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.2); text-align: left; }
    th { font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.7; }
    .num { font-variant-numeric: tabular-nums; white-space: nowrap; }
    .rec { font-weight: 700; }
    .row { cursor: pointer; }
    .row:hover { background: rgba(52,152,219,0.08); }
    tr.mine { box-shadow: inset 3px 0 0 #27ae60; }
    .pair { white-space: nowrap; }
    .vs { opacity: 0.5; margin: 0 0.3em; }
    .lead { color: #27ae60; font-weight: 600; }
    .chip { display: inline-block; font-size: 0.8em; border: 1px solid rgba(127,127,127,0.35); border-radius: 999px;
            padding: 0.05em 0.5em; margin: 0.1em 0.2em 0.1em 0; white-space: nowrap; }
    .streak { white-space: nowrap; font-size: 0.9em; }
    .games td { background: rgba(127,127,127,0.06); }
    .gl { display: grid; gap: 0.25em; font-size: 0.88em; }
    .g { display: flex; flex-wrap: wrap; gap: 0.3em; align-items: baseline; }
    .when { opacity: 0.65; min-width: 6.5em; }
    .won { font-weight: 700; color: #27ae60; }
    .po { font-size: 0.8em; opacity: 0.7; font-style: italic; }
    small.h { display: block; font-size: 0.75em; opacity: 0.6; }
    .dim { opacity: 0.4; }
    @media (max-width: 640px) {
        .wide { display: none; }
        .controls label { display: flex; align-items: center; gap: 0.4em; }
        select { margin-left: 0; }
        .split .chip { display: block; width: max-content; }
        th, td { padding: 0.4em 0.3em; }
    }
</style>
