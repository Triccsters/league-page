<script>
    // Two ways of asking whether a record was earned: a median game (did you beat
    // half the league that week?) and strength of schedule (who did you have to play?).
    import { onMount } from 'svelte';
    import { games, nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import odds from '$lib/data/odds.json';

    let ready = false;
    onMount(() => { ready = true; });

    const reg = games.filter(g => !g.playoff);
    const seasons = [...new Set(reg.map(g => g.season))].sort((a, b) => b - a);
    const curWeeks = new Set(reg.filter(g => g.season === site.season).map(g => g.week)).size;
    let season = seasons[0] === site.season && curWeeks < 2 && seasons[1] ? seasons[1] : seasons[0];

    const r1 = (v) => Math.round(v * 10) / 10;

    function build(s) {
        const rows = {};
        const row = (h) => (rows[h] ||= { h, w: 0, l: 0, mw: 0, ml: 0, pf: 0, g: 0, opp: [] });
        const byWeek = {};
        for (const g of reg.filter(g => g.season === s)) {
            (byWeek[g.week] ||= []).push([g.a, g.pa], [g.b, g.pb]);
            for (const [me, mp, them, op] of [[g.a, g.pa, g.b, g.pb], [g.b, g.pb, g.a, g.pa]]) {
                const r = row(me);
                r.g++; r.pf += mp; r.opp.push(them);
                if (mp > op) r.w++; else if (mp < op) r.l++;
            }
        }
        // the median game: beat the middle of the league that week and it counts as a win
        for (const list of Object.values(byWeek)) {
            const sorted = list.map(([, p]) => p).sort((a, b) => a - b);
            const n = sorted.length;
            if (n < 4) continue;
            const med = n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
            for (const [h, p] of list) {
                const r = row(h);
                if (p > med) r.mw++; else if (p < med) r.ml++;
            }
        }
        const avg = {};
        for (const r of Object.values(rows)) avg[r.h] = r.g ? r.pf / r.g : 0;
        const out = Object.values(rows).map(r => {
            const faced = r.opp.length ? r.opp.reduce((t, o) => t + (avg[o] || 0), 0) / r.opp.length : 0;
            return {
                ...r,
                ppg: r1(r.pf / Math.max(1, r.g)),
                faced: r1(faced),
                tw: r.w + r.mw,
                tl: r.l + r.ml,
            };
        });
        // rank by the real record, then by the combined record, to show who moves
        const byReal = [...out].sort((a, b) => b.w - a.w || b.pf - a.pf);
        const byBoth = [...out].sort((a, b) => b.tw - a.tw || b.pf - a.pf);
        byReal.forEach((r, i) => (r.rank = i + 1));
        byBoth.forEach((r, i) => (r.mrank = i + 1));
        return byBoth.map(r => ({ ...r, move: r.rank - r.mrank }));
    }

    $: table = build(+season);
    $: swing = table.map(r => ({
        label: nameOf(r.h),
        value: r.move,
        note: r.move === 0 ? 'same seed' : (r.move > 0 ? `up ${r.move}` : `down ${-r.move}`),
        highlight: ready && r.h === $myTeam,
        color: r.move > 0 ? '#27ae60' : (r.move < 0 ? '#e74c3c' : '#7f8c8d'),
    }));
    $: sosBars = table
        .slice()
        .sort((a, b) => b.faced - a.faced)
        .map(r => ({
            label: nameOf(r.h),
            value: r.faced,
            note: `${r.w}-${r.l}, scored ${r.ppg}/wk`,
            highlight: ready && r.h === $myTeam,
        }));

    // the rest of this season comes from the odds build
    $: showRest = +season === site.season && odds && odds.season === site.season;
    $: rest = !showRest ? [] : odds.teams
        .filter(t => t.sos_rest)
        .slice()
        .sort((a, b) => b.sos_rest - a.sos_rest)
        .map(t => ({
            label: nameOf(t.h),
            value: r1(t.sos_rest),
            note: `${t.rest_opponents ? t.rest_opponents.length : 0} games left`,
            highlight: ready && t.h === $myTeam,
        }));
</script>

<div class="holder">
    <h1>Median Standings &amp; Schedule Strength</h1>
    <p class="sub">
        Two ways of asking whether a record was earned. The <b>median game</b> is a second, imaginary matchup each
        week against the middle of the league: score above the median and it is a win. It rewards scoring and takes
        the luck of the draw out. <b>Schedule strength</b> is the average points per week scored by the teams you
        actually had to play. Neither changes the real standings — this league does not use a median game.
    </p>

    <div class="filters">
        <select bind:value={season}>
            {#each seasons as s}<option value={s}>{s}{s === site.season ? ' (so far)' : ''}</option>{/each}
        </select>
    </div>

    <h2>With a median game added</h2>
    <p class="note">Seeded by the combined record. "Moves" is how far a team shifts from where the real record has them.</p>
    <div class="scroll">
        <table>
            <thead><tr>
                <th class="num">#</th><th>Manager</th><th class="num">Real</th><th class="num">Vs median</th>
                <th class="num">Combined</th><th class="num">Moves</th><th class="num">Points/wk</th>
            </tr></thead>
            <tbody>
                {#each table as r}
                    <tr class:mine={ready && r.h === $myTeam}>
                        <td class="num">{r.mrank}</td>
                        <td>{#if managerLink(r.h)}<a href={managerLink(r.h)}>{nameOf(r.h)}</a>{:else}{nameOf(r.h)}{/if}</td>
                        <td class="num">{r.w}-{r.l}</td>
                        <td class="num">{r.mw}-{r.ml}</td>
                        <td class="num"><b>{r.tw}-{r.tl}</b></td>
                        <td class="num" class:pos={r.move > 0} class:neg={r.move < 0}>
                            {r.move === 0 ? '—' : (r.move > 0 ? `▲ ${r.move}` : `▼ ${-r.move}`)}
                        </td>
                        <td class="num">{r.ppg}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <h2>Seeds gained or lost</h2>
    <HBarChart items={swing} format={(v) => (v > 0 ? `+${v}` : `${v}`)} ariaLabel="Seed change with a median game in {season}" />

    <h2>Who they had to play</h2>
    <p class="note">Average points per week scored by their opponents this season. Higher means a harder run.</p>
    <HBarChart items={sosBars} ariaLabel="Strength of schedule faced in {season}" />

    {#if showRest && rest.length}
        <h2>What is left this season</h2>
        <p class="note">Average strength of the opponents still on the schedule, from the same model the playoff odds use.</p>
        <HBarChart items={rest} ariaLabel="Remaining strength of schedule" />
    {/if}
</div>

<style>
    .holder { max-width: 1000px; margin: 0 auto 3em; padding: 0 1em; text-align: left; }
    h1 { margin-bottom: 0.2em; }
    h2 { margin: 1.8em 0 0.1em; font-size: 1.1em; }
    .sub { opacity: 0.75; font-size: 0.9em; max-width: 62em; }
    .note { opacity: 0.65; font-size: 0.8em; margin: 0.2em 0 0.6em; }
    .filters { margin: 1em 0 0.4em; }
    select { padding: 0.35em 0.5em; font-size: 0.9em; }
    .scroll { overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
    th, td { padding: 0.35em 0.6em; border-bottom: 1px solid rgba(127,127,127,0.2); text-align: left; white-space: nowrap; }
    th { font-weight: 600; opacity: 0.75; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    tr.mine { background: rgba(52,152,219,0.14); }
    td a { color: #3498db; }
    .pos { color: #27ae60; }
    .neg { color: #e74c3c; }
</style>
