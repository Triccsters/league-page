<script>
    // Projected vs actual, position-group surprises and the weekly score spread.
    // Data: src/lib/data/insights.json, written by scripts/insights.py every Tuesday.
    import { onMount } from 'svelte';
    import data from '$lib/data/insights.json';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import StripChart from '$lib/Charts/StripChart.svelte';

    let ready = false;
    onMount(() => { ready = true; });

    const sign = (v) => (v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1));
    const POS = { QB: 'QB', RB: 'running back', WR: 'receiver', TE: 'tight end' };
    const ordinal = (n) => n + (['th', 'st', 'nd', 'rd'][(n % 100 - 20) % 10] || ['th', 'st', 'nd', 'rd'][n % 100] || 'th');

    $: bars = data.projections ? data.teams.map(t => ({
        label: nameOf(t.name), value: Math.round(t.d * 10) / 10,
        note: `${t.beat} of ${t.beat + t.missed} weeks over`,
        highlight: ready && t.name === $myTeam, color: t.d >= 0 ? '#27ae60' : '#e74c3c',
    })) : [];

    $: spread = data.teams.map(t => ({
        label: nameOf(t.name), values: t.weeks.map(w => w.act),
        highlight: ready && t.name === $myTeam,
    })).sort((a, b) => median(b.values) - median(a.values));
    function median(v) { const s = [...v].sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : 0; }

    // the newest weeks first; at most the last three weeks with anything to say
    $: surpriseWeeks = [...new Set(data.surprises.map(s => s.w))].slice(0, 3);
</script>

<div class="holder">
    <h1>Insights</h1>
    <p class="sub">Projected against actual, and position groups that suddenly broke out or fell apart. {data.season} regular season{data.through_week ? `, through week ${data.through_week}` : ''}.</p>
    {#if data.stale}<p class="note warn">Sleeper's projections did not answer at the last update, so this page is from the update before.</p>{/if}

    {#if data.projections}
        <h2>Who beat their projections</h2>
        <p class="note">Each starter's projection, added up and scored the way this league scores. Above zero means the lineup outscored what it was projected to.</p>
        <HBarChart items={bars} format={sign} ariaLabel="Points above or below projection, season to date" />

        <div class="scroll">
            <table>
                <thead><tr><th>Manager</th><th class="num">Projected</th><th class="num">Actual</th><th class="num">+/-</th><th class="num">Weeks over</th></tr></thead>
                <tbody>
                    {#each data.teams as t}
                        <tr class:mine={ready && t.name === $myTeam}>
                            <td>{#if managerLink(t.name)}<a href={managerLink(t.name)}>{nameOf(t.name)}</a>{:else}{nameOf(t.name)}{/if}</td>
                            <td class="num">{t.proj.toFixed(1)}</td><td class="num">{t.act.toFixed(1)}</td>
                            <td class="num" class:pos={t.d > 0} class:neg={t.d < 0}>{sign(t.d)}</td>
                            <td class="num">{t.beat} of {t.beat + t.missed}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        {#if data.week_best.length}
            <div class="two">
                <section>
                    <h3>Week {data.through_week}: beat their projection</h3>
                    {#each data.week_best as p}<p><b>{p.n}</b> <span class="muted">{p.p}, {nameOf(p.h)}</span> {p.act} vs {p.proj} <span class="pos">{sign(p.d)}</span></p>{/each}
                </section>
                <section>
                    <h3>Week {data.through_week}: fell short</h3>
                    {#each data.week_worst as p}<p><b>{p.n}</b> <span class="muted">{p.p}, {nameOf(p.h)}</span> {p.act} vs {p.proj} <span class="neg">{sign(p.d)}</span></p>{/each}
                </section>
            </div>
        {/if}
    {:else}
        <p class="note">Projected vs actual isn't available for this league: most of its players come from ESPN and can't be matched to Sleeper's projections.</p>
    {/if}

    <h2>Position groups that surprised</h2>
    {#if !data.positions}
        <p class="note">Not available for this league: too many players can't be matched to a position.</p>
    {:else if !surpriseWeeks.length}
        <p class="note">Nothing yet. A group needs three weeks of history before a week can stand out.</p>
    {:else}
        <p class="note">A weak group (bottom third of the league at that position) that suddenly put up a big week, or a strong group that fell apart. Starters only; kickers and defences left out because they swing every week.</p>
        {#each surpriseWeeks as w}
            <h3>Week {w}</h3>
            {#each data.surprises.filter(s => s.w === w) as s}
                <p class="surprise" class:mine={ready && s.h === $myTeam}>
                    <span class="tag" class:up={s.kind === 'breakout'} class:down={s.kind === 'collapse'}>{s.kind === 'breakout' ? 'Breakout' : 'Collapse'}</span>
                    <b>{nameOf(s.h)}</b>'s {POS[s.pos] || s.pos} group scored <b>{s.pts}</b>. Before this week it averaged {s.avg}, {ordinal(s.of - s.rank + 1)} best of {s.of} in the league (league average {s.league}).
                </p>
            {/each}
        {/each}
    {/if}

    <h2>Weekly scores, every team</h2>
    <p class="note">One dot per week. A tight row is a steady team; a wide one is boom or bust. Sorted by median score; the line is each team's median.</p>
    <StripChart rows={spread} ariaLabel="Weekly scores by team" />

    <p class="note small">Projections: {data.source}. Sleeper's projection feed isn't part of its public API, and Sleeper data is for non-commercial use.</p>
</div>

<style>
    .holder { max-width: 900px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { font-size: 1em; margin: 1em 0 0.3em; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .small { font-size: 0.8em; margin-top: 2em; }
    .warn { color: #e67e22; opacity: 1; }
    .scroll { overflow-x: auto; margin-top: 1em; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.9em; white-space: nowrap; }
    td a { color: inherit; font-weight: 600; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .pos { color: #2ecc71; font-weight: 700; }
    .neg { color: #e74c3c; font-weight: 700; }
    .muted { opacity: 0.65; font-size: 0.9em; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0 2em; }
    .two p { margin: 0.3em 0; font-size: 0.9em; }
    .surprise { margin: 0.4em 0; font-size: 0.92em; line-height: 1.5; padding: 0.2em 0.4em; border-radius: 6px; }
    .surprise.mine { background: rgba(39, 174, 96, 0.15); }
    .tag { display: inline-block; font-size: 0.75em; font-weight: 700; padding: 0.1em 0.5em; border-radius: 99px; margin-right: 0.4em; color: #fff; }
    .tag.up { background: #27ae60; }
    .tag.down { background: #c0392b; }
</style>