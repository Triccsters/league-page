<script>
    // What the waiver wire actually returned: points a pickup scored while started
    // for the manager who claimed him. Players that manager drafted that season
    // are excluded, so this is free-agent value only.
    import { onMount } from 'svelte';
    import { nameOf, managerLink, currentManagers, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    let data = null;
    let failed = false;
    let ready = false;
    let season = 'all';
    let sort = 'pts';

    onMount(async () => {
        ready = true;
        try {
            const r = await fetch('/data/waivers.json');
            if (!r.ok) throw new Error(r.status);
            data = await r.json();
        } catch (e) {
            failed = true;
        }
    });

    const current = new Set(currentManagers);
    const r1 = (v) => Math.round(v * 10) / 10;

    $: seasons = !data ? [] : [...new Set(data.pickups.map(p => p.season))].sort((a, b) => b - a);
    $: pickups = !data ? [] : data.pickups
        .filter(p => season === 'all' || p.season === +season)
        .slice()
        .sort((a, b) => (sort === 'pts' ? b.pts - a.pts : (b.faab || 0) - (a.faab || 0) || b.pts - a.pts));

    // per-manager, current managers only, sorted by what the wire gave them
    $: table = !data ? [] : Object.entries(data.managers)
        .filter(([h]) => current.has(h))
        .map(([h, m]) => ({ h, ...m }))
        .sort((a, b) => b.pts - a.pts);

    $: bars = table
        .slice()
        .sort((a, b) => b.per_add - a.per_add)
        .map(m => ({
            label: nameOf(m.h),
            value: r1(m.per_add),
            note: `${m.adds} adds, ${Math.round(m.pts)} pts`,
            highlight: ready && m.h === $myTeam,
        }));
</script>

<div class="holder">
    <h1>Waiver Returns</h1>
    <p class="sub">
        Points a player scored <b>while in the starting lineup</b> after the manager picked him up, going back to
        {data ? data.first_season : ''}. Anyone that manager drafted that season is left out, so what is left is what
        the wire gave them. FAAB figures start in {data ? data.faab_from : ''}, and only some claims carry a bid.
    </p>

    {#if data}
        <h2>Points per add</h2>
        <p class="note">Total free-agent points divided by claims made. Volume is on the label.</p>
        <HBarChart items={bars} ariaLabel="Waiver points per add" />

        <div class="scroll">
            <table>
                <thead><tr>
                    <th>Manager</th><th class="num">Adds</th><th class="num">Points</th>
                    <th class="num">Per add</th><th class="num">FAAB</th><th class="num">Per $</th><th class="num">Hits</th>
                </tr></thead>
                <tbody>
                    {#each table as m}
                        <tr class:mine={ready && m.h === $myTeam}>
                            <td>{#if managerLink(m.h)}<a href={managerLink(m.h)}>{nameOf(m.h)}</a>{:else}{nameOf(m.h)}{/if}</td>
                            <td class="num">{m.adds}</td>
                            <td class="num">{Math.round(m.pts)}</td>
                            <td class="num">{r1(m.per_add)}</td>
                            <td class="num">{m.faab ? `$${m.faab}` : '—'}</td>
                            <td class="num">{m.per_dollar ? r1(m.per_dollar) : '—'}</td>
                            <td class="num">{m.hits}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
        <p class="note">A "hit" is a pickup that went on to score 50 or more points in the starting lineup.</p>

        <h2>Best claims on record</h2>
        <div class="filters">
            <select bind:value={season}>
                <option value="all">All seasons</option>
                {#each seasons as s}<option value={s}>{s}</option>{/each}
            </select>
            <select bind:value={sort}>
                <option value="pts">Most points</option>
                <option value="faab">Biggest bid</option>
            </select>
        </div>
        <div class="scroll">
            <table>
                <thead><tr><th class="num">#</th><th>Player</th><th>Picked up by</th><th class="num">Season</th><th class="num">Starts</th><th class="num">FAAB</th><th class="num">Points</th></tr></thead>
                <tbody>
                    {#each pickups.slice(0, 60) as p, i}
                        <tr class:mine={ready && p.h === $myTeam}>
                            <td class="num">{i + 1}</td>
                            <td><b>{p.n}</b></td>
                            <td>{#if managerLink(p.h)}<a href={managerLink(p.h)}>{nameOf(p.h)}</a>{:else}{nameOf(p.h)}{/if}</td>
                            <td class="num">{p.season}</td>
                            <td class="num">{p.st}</td>
                            <td class="num">{p.faab ? `$${p.faab}` : '—'}</td>
                            <td class="num">{r1(p.pts)}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
        <p class="note">{data.count.toLocaleString()} claims on record. The table shows the best 60 that match.</p>
    {:else if failed}
        <p class="err">Waiver data could not be loaded.</p>
    {:else}
        <p class="sub">Loading…</p>
    {/if}
</div>

<style>
    .holder { max-width: 1000px; margin: 0 auto 3em; padding: 0 1em; text-align: left; }
    h1 { margin-bottom: 0.2em; }
    h2 { margin: 1.6em 0 0.1em; font-size: 1.1em; }
    .sub { opacity: 0.75; font-size: 0.9em; max-width: 60em; }
    .note { opacity: 0.65; font-size: 0.8em; margin: 0.2em 0 0.6em; }
    .filters { margin: 0.6em 0; display: flex; gap: 0.5em; flex-wrap: wrap; }
    select { padding: 0.35em 0.5em; font-size: 0.9em; }
    .scroll { overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
    th, td { padding: 0.35em 0.6em; border-bottom: 1px solid rgba(127,127,127,0.2); text-align: left; white-space: nowrap; }
    th { font-weight: 600; opacity: 0.75; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    tr.mine { background: rgba(52,152,219,0.14); }
    td a { color: #3498db; }
    .err { color: #e74c3c; }
</style>
