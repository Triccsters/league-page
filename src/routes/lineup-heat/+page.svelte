<script>
    // Lineup heat map: every manager's current starters, one column per lineup slot, coloured by points
    // per game against the rest of the league at that slot. Idea from a league site T.J. shared 2026-11-13.
    import { onMount } from 'svelte';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import * as leagueInfo from '$lib/utils/leagueInfo';

    let data = null, error = '', ready = false;
    onMount(async () => {
        ready = true;
        try { data = await fetch('/data/rosters.json').then((r) => r.json()); }
        catch (e) { error = 'Could not load the rosters.'; }
    });
    const ORDER = ['QB', 'RB', 'WR', 'TE', 'FLEX', 'WRRB_FLEX', 'REC_FLEX', 'SUPER_FLEX', 'K', 'DEF'];
    const LABEL = { FLEX: 'FLEX', WRRB_FLEX: 'W/R', REC_FLEX: 'W/T', SUPER_FLEX: 'SUPERFLEX' };
    const val = (p) => (p.rate ?? null);

    $: rows = !data ? [] : Object.entries(data.managers || {}).map(([h, m]) => {
        const by = {};
        for (const p of (m.players || []).filter((p) => p.st && p.slot && p.slot !== 'BENCH')) (by[p.slot] ||= []).push(p);
        for (const k in by) by[k].sort((a, b) => (val(b) ?? -1) - (val(a) ?? -1));
        const total = Object.values(by).flat().reduce((s, p) => s + (val(p) || 0), 0);
        return { h, by, total };
    }).filter((r) => Object.keys(r.by).length).sort((a, b) => b.total - a.total);
    $: slots = ORDER.filter((s) => rows.some((r) => r.by[s]));
    $: cols = slots.flatMap((s) => {
        const n = Math.max(...rows.map((r) => (r.by[s] || []).length));
        return Array.from({ length: n }, (_, i) => ({ s, i, label: (LABEL[s] || s) + (n > 1 || !LABEL[s] ? i + 1 : '') }));
    });
    // rank each cell among all starters at the same slot type
    $: sorted = Object.fromEntries(slots.map((s) => [s, rows.flatMap((r) => r.by[s] || []).map(val).filter((v) => v != null).sort((a, b) => a - b)]));
    const heat = (p, arr) => {
        const v = val(p);
        if (v == null || !arr || arr.length < 2) return 'background:#3a3f44';
        const t = arr.filter((x) => x < v).length / (arr.length - 1);
        return `background:hsl(${Math.round(120 * Math.min(1, t))}, 78%, ${Math.round(24 + 8 * Math.min(1, t))}%)`;
    };
</script>

<svelte:head><title>Lineup Heat Map | {leagueInfo.leagueName || 'League'}</title></svelte:head>

<div class="holder">
    <h1>Lineup Heat Map</h1>
    {#if data && rows.length}
        <p class="sub">Every manager's starting lineup right now. Green is one of the best starters in the league at that spot by points per game this season, red is one of the weakest. Teams are in order of total lineup strength.</p>
        <div class="scroll">
            <table>
                <thead><tr><th>Manager</th>{#each cols as c}<th>{c.label}</th>{/each}</tr></thead>
                <tbody>
                    {#each rows as r (r.h)}
                        <tr class:mine={ready && r.h === $myTeam}>
                            <td class="who">{#if managerLink(r.h)}<a href={managerLink(r.h)}>{nameOf(r.h)}</a>{:else}{nameOf(r.h)}{/if}</td>
                            {#each cols as c}
                                {@const p = (r.by[c.s] || [])[c.i]}
                                {#if p}<td class="cell" style={heat(p, sorted[c.s])} title="{p.p} · {p.t || ''} · {val(p) ?? 'no'} points per game">{p.n}<small>{val(p) ?? ''}</small></td>
                                {:else}<td class="cell none">empty</td>{/if}
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
        <p class="note">Updated {data.generated ? new Date(data.generated).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'daily'}. A player with no games this season shows grey.</p>
    {:else if data}
        <p class="sub">No starting lineups on record for this league yet.</p>
    {:else if error}
        <p class="sub">{error}</p>
    {:else}
        <p class="sub">Loading lineups…</p>
    {/if}
</div>

<style>
    .holder { max-width: 1250px; margin: 0 auto; padding: 1.2em 0.8em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub, .note { text-align: center; opacity: 0.8; font-size: 0.92em; line-height: 1.5; max-width: 760px; margin: 0.4em auto 1em; }
    .scroll { overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; }
    th { background: #23282c; color: #fff; text-align: left; font-size: 0.8em; padding: 0.55em 0.6em; border: 1px solid #3a3f44; white-space: nowrap; }
    td { border: 1px solid #23282c; padding: 0.5em 0.6em; font-size: 0.86em; }
    .who { background: #23282c; color: #fff; font-weight: 700; white-space: nowrap; position: sticky; left: 0; }
    .who a { color: inherit; }
    tr.mine .who { box-shadow: inset 4px 0 0 #2ecc71; }
    .cell { color: #fff; min-width: 6.5em; line-height: 1.25; }
    .cell small { display: block; opacity: 0.8; font-size: 0.8em; }
    .cell.none { background: #2b2f33; color: #9aa5ab; font-style: italic; }
</style>
