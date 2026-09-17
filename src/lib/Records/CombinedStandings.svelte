<script>
    // All-time table for every manager across every platform the league has used,
    // plus a win-rate chart and a champions timeline.
    import { onMount } from 'svelte';
    import { games, nameOf, managers, currentManagers, generated, site, hasYahoo } from '$lib/utils/flpHistory';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });

    const REAL = new Set(['Quarterfinal', 'Semifinal', 'Championship']);
    const current = new Set(currentManagers);
    let showFormer = true;
    const rows = {};
    const row = (h) => (rows[h] ||= { h, seasons: new Set(), w: 0, l: 0, t: 0, pf: 0, g: 0,
        pw: 0, pl: 0, titles: [], finals: 0, yahoo: [0, 0], sleeper: [0, 0], live: [0, 0] });
    const champs = {};   // season -> { winner, loser, score }

    for (const g of games) {
        if (g.label === 'Championship') {
            const aw = g.pa > g.pb;
            champs[g.season] = { winner: aw ? g.a : g.b, loser: aw ? g.b : g.a,
                score: `${Math.max(g.pa, g.pb).toFixed(2)}–${Math.min(g.pa, g.pb).toFixed(2)}` };
        }
        for (const [me, mp, op] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
            const r = row(me);
            r.seasons.add(g.season);
            const won = mp > op, lost = mp < op;
            if (!g.playoff) {
                r.g++; r.pf += mp;
                if (won) r.w++; else if (lost) r.l++; else r.t++;
                const era = g.era === 'yahoo' ? r.yahoo : r.sleeper;
                if (won) era[0]++; else if (lost) era[1]++;
                if (g.season === site.season) { if (won) r.live[0]++; else if (lost) r.live[1]++; }
            } else if (REAL.has(g.label)) {
                if (won) r.pw++; else if (lost) r.pl++;
                if (g.label === 'Championship') {
                    r.finals++;
                    if (won) r.titles.push(g.season);
                }
            }
        }
    }

    const list = Object.values(rows)
        .map(r => ({ ...r, last: Math.max(...r.seasons), former: !current.has(r.h), pct: r.g ? (r.w + r.t / 2) / r.g : 0, avg: r.g ? r.pf / r.g : 0 }))
        .sort((a, b) => b.titles.length - a.titles.length || b.pct - a.pct);
    const formerCount = list.filter(r => r.former).length;
    const pct = (x) => (x * 100).toFixed(1) + '%';
    const first = site.first_season;
    const last = Math.max(...games.map(g => g.season));
    const seasonsWithFinal = Object.keys(champs).map(Number).sort((a, b) => a - b);

    $: shown = showFormer ? list : list.filter(r => !r.former);
    $: winBars = [...shown].sort((a, b) => b.pct - a.pct).map(r => ({
        label: nameOf(r.h), value: Math.round(r.pct * 1000) / 10, note: `${r.w}-${r.l}`,
        highlight: ready && r.h === $myTeam, former: r.former,
    }));
    $: titleBars = shown.filter(r => r.finals).map(r => ({
        label: nameOf(r.h), value: r.titles.length,
        note: `${r.finals} final${r.finals > 1 ? 's' : ''}`,
        color: '#f1c40f', highlight: ready && r.h === $myTeam, former: r.former,
    }));
</script>

<h2>🏈 All-time, every season ({first}–{last})</h2>
<p class="note">One row per person{hasYahoo ? ' across Yahoo and Sleeper' : ''}. W-L is regular season only; the playoff record counts real playoff rounds, not consolation games.
    Records include the {site.season} season so far (shown in green under the record).
    {#if formerCount}Faded rows marked <span class="ftag">Left league in …</span> are managers no longer in the league.{/if}</p>
{#if formerCount}
    <label class="toggle"><input type="checkbox" bind:checked={showFormer} /> Show {formerCount} former manager{formerCount > 1 ? 's' : ''}</label>
{/if}
<div class="scroll">
<table>
    <thead>
        <tr><th>#</th><th>Manager</th><th>Seasons</th><th>W-L-T</th><th>Win %</th>
            {#if hasYahoo}<th>Yahoo</th><th>Sleeper</th>{/if}
            <th class="num">PF/game</th><th>Playoffs</th><th>🏆</th><th>Finals</th></tr>
    </thead>
    <tbody>
        {#each shown as r, i}
            <tr class:mine={ready && r.h === $myTeam} class:former={r.former}>
                <td>{i + 1}</td>
                <td><b>{nameOf(r.h)}</b>{#if r.former}<span class="ftag">Left league in {r.last + 1}</span>{/if}{#if managers[r.h]?.yahoo && managers[r.h].yahoo !== nameOf(r.h)} <small>({managers[r.h].yahoo} on Yahoo)</small>{/if}<YourTeamBadge handle={r.h} size="small" /></td>
                <td>{r.seasons.size}</td>
                <td>{r.w}-{r.l}{r.t ? `-${r.t}` : ''}{#if r.live[0] + r.live[1]}<span class="live">{r.live[0]}-{r.live[1]} in {site.season}</span>{/if}</td>
                <td>{pct(r.pct)}</td>
                {#if hasYahoo}
                    <td>{r.yahoo[0] + r.yahoo[1] ? `${r.yahoo[0]}-${r.yahoo[1]}` : '—'}</td>
                    <td>{r.sleeper[0] + r.sleeper[1] ? `${r.sleeper[0]}-${r.sleeper[1]}` : '—'}</td>
                {/if}
                <td class="num">{r.avg.toFixed(1)}</td>
                <td>{r.pw}-{r.pl}</td>
                <td>{r.titles.length ? `${r.titles.length} (${r.titles.join(', ')})` : '—'}</td>
                <td>{r.finals}</td>
            </tr>
        {/each}
    </tbody>
</table>
</div>

<div class="charts">
    <div>
        <h3>Regular-season win %</h3>
        <HBarChart items={winBars} refLine={{ value: 50, label: '.500' }} format={(v) => `${v}%`} ariaLabel="All-time win percentage" />
    </div>
    {#if titleBars.length}
    <div>
        <h3>Titles</h3>
        <HBarChart items={titleBars} ariaLabel="Championships by manager" />
    </div>
    {/if}
</div>

{#if seasonsWithFinal.length}
    <h3>Every final</h3>
    <div class="finals">
        {#each seasonsWithFinal as s}
            {@const c = champs[s]}
            <div class="final" class:mine={ready && (c.winner === $myTeam || c.loser === $myTeam)}>
                <span class="yr">{s}</span>
                <b>🏆 {nameOf(c.winner)}{#if !current.has(c.winner)} <span class="ftag">FORMER</span>{/if}</b>
                <span class="ru">over {nameOf(c.loser)}{!current.has(c.loser) ? ' (former)' : ''}</span>
                <span class="sc">{c.score}</span>
            </div>
        {/each}
    </div>
{/if}
<p class="note">Data updated {generated.slice(0, 10)}.</p>

<style>
    .note { opacity: 0.7; font-size: 0.9em; }
    .toggle { display: block; margin: 0.3em 0 0.6em; font-size: 0.9em; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.25); text-align: left; font-size: 0.92em; white-space: nowrap; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    tr.former td { opacity: 0.55; }
    .ftag { display: inline-block; text-transform: uppercase; margin-left: 0.45em; padding: 0.05em 0.4em; border-radius: 3px; font-size: 0.68em; font-weight: 700;
        letter-spacing: 0.04em; background: #5d6d7e; color: #fff; vertical-align: middle; opacity: 1; }
    .live { display: block; font-size: 0.75em; font-weight: 600; color: #2ecc71; }
    .num { text-align: right; }
    small { opacity: 0.6; }
    h3 { margin: 1.2em 0 0.2em; text-align: left; }
    .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0 2em; }
    .finals { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.5em; margin: 0.5em 0 1em; text-align: left; }
    .final { border: 1px solid rgba(127,127,127,0.35); border-left: 4px solid #f1c40f; border-radius: 6px; padding: 0.4em 0.6em; display: flex; flex-direction: column; font-size: 0.88em; }
    .final.mine { border-color: #27ae60; }
    .yr { opacity: 0.7; font-size: 0.85em; }
    .ru, .sc { opacity: 0.75; font-size: 0.85em; }
</style>
