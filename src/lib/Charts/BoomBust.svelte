<script>
    // Boom or bust: how often each player lands far above or below his own
    // projection, and which lineups have boomed or busted most. Data comes
    // from insights.json ("boombust"), written by scripts/insights.py.
    import { onMount } from 'svelte';
    import { nameOf } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    export let bb;

    let ready = false;
    onMount(() => { ready = true; });
    let pos = 'ALL', team = 'ALL', label = 'ALL';
    const POS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
    const LABELS = ['Boom or bust', 'Booming', 'Steady', 'Mixed', 'Busting'];
    $: teamsList = [...new Set(bb.players.map((p) => p.h))].sort((a, b) => nameOf(a).localeCompare(nameOf(b)));
    $: rows = bb.players
        .filter((p) => pos === 'ALL' || p.p === pos)
        .filter((p) => team === 'ALL' || p.h === team)
        .filter((p) => label === 'ALL' || p.label === label)
        .slice(0, 40);
    const tone = (l) => ({ 'Boom or bust': 'bb', Booming: 'up', Busting: 'down', Steady: 'steady' }[l] || '');
</script>

<h2>Boom or bust</h2>
<p class="note">{bb.rule} Every rostered player counts, bench included.</p>

<div class="filters">
    <select bind:value={pos}><option value="ALL">All positions</option>{#each POS as p}<option>{p}</option>{/each}</select>
    <select bind:value={team}><option value="ALL">All teams</option>{#each teamsList as h}<option value={h}>{nameOf(h)}</option>{/each}</select>
    <select bind:value={label}><option value="ALL">Every type</option>{#each LABELS as l}<option>{l}</option>{/each}</select>
</div>
<div class="scroll">
    <table>
        <thead><tr><th>Player</th><th>Team</th><th class="num">Wks</th><th class="num">Avg</th><th class="num">Proj</th><th class="num">High</th><th class="num">Low</th><th class="num">Boom</th><th class="num">Bust</th><th>Type</th></tr></thead>
        <tbody>
            {#each rows as p}
                <tr class:mine={ready && p.h === $myTeam}>
                    <td><b>{p.n}</b> <span class="muted">{p.p}</span></td><td>{nameOf(p.h)}</td>
                    <td class="num">{p.g}</td><td class="num">{p.avg}</td><td class="num">{p.proj}</td>
                    <td class="num">{p.hi}</td><td class="num">{p.lo}</td>
                    <td class="num up">{p.boom}</td><td class="num down">{p.bust}</td>
                    <td><span class="tag {tone(p.label)}">{p.label}</span></td>
                </tr>
            {:else}
                <tr><td colspan="10" class="muted">Nobody matches.</td></tr>
            {/each}
        </tbody>
    </table>
</div>

<h3>Lineups that boomed and busted</h3>
<p class="note">Starters only. Booms minus busts, season to date.</p>
<div class="scroll">
    <table>
        <thead><tr><th>Team</th><th class="num">Starts</th><th class="num">Booms</th><th class="num">Busts</th><th class="num">Net</th></tr></thead>
        <tbody>
            {#each bb.teams as t}
                <tr class:mine={ready && t.h === $myTeam}><td>{nameOf(t.h)}</td><td class="num">{t.starts}</td><td class="num up">{t.boom}</td><td class="num down">{t.bust}</td><td class="num" class:up={t.boom > t.bust} class:down={t.boom < t.bust}>{t.boom - t.bust > 0 ? '+' : ''}{t.boom - t.bust}</td></tr>
            {/each}
        </tbody>
    </table>
</div>

<style>
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { font-size: 1em; margin: 1.4em 0 0.3em; }
    .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .filters { display: flex; gap: 0.5em; justify-content: center; flex-wrap: wrap; margin: 0.6em 0; }
    .filters select { font: inherit; font-size: 0.9em; padding: 0.25em 0.4em; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.35em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.88em; white-space: nowrap; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .up { color: #2ecc71; font-weight: 700; }
    .down { color: #e74c3c; font-weight: 700; }
    .muted { opacity: 0.65; font-size: 0.9em; }
    .tag { font-size: 0.75em; font-weight: 800; color: #fff; border-radius: 4px; padding: 0.15em 0.45em; background: #566573; }
    .tag.bb { background: #ca6f1e; } .tag.up { background: #1e8449; color: #fff; } .tag.down { background: #c0392b; color: #fff; } .tag.steady { background: #2471a3; }
</style>
