<script>
    // Luck = actual regular-season wins minus the wins you'd expect if you played every team every week.
    import { onMount } from 'svelte';
    import { games, nameOf, managerLink, currentManagers, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    let ready = false;
    onMount(() => { ready = true; });
    const current = new Set(currentManagers);
    const reg = games.filter(g => !g.playoff);
    const seasons = [...new Set(reg.map(g => g.season))].sort((a, b) => b - a);
    // open on the current season once it has a few weeks, otherwise last season
    const curWeeks = new Set(reg.filter(g => g.season === site.season).map(g => g.week)).size;
    let season = seasons[0] === site.season && curWeeks < 4 && seasons[1] ? seasons[1] : seasons[0];

    function seasonTable(s) {
        const t = {};
        const row = (h) => (t[h] ||= { h, w: 0, l: 0, aw: 0, al: 0, pf: 0, pa: 0, g: 0 });
        const weeks = {};
        for (const g of reg.filter(g => g.season === s)) {
            (weeks[g.week] ||= []).push([g.a, g.pa], [g.b, g.pb]);
            for (const [me, mp, op] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
                const r = row(me);
                r.g++; r.pf += mp; r.pa += op;
                if (mp > op) r.w++; else if (mp < op) r.l++;
            }
        }
        for (const list of Object.values(weeks)) {
            for (const [h, p] of list) {
                const r = row(h);
                r.aw += list.filter(([o, q]) => o !== h && q < p).length;
                r.al += list.filter(([o, q]) => o !== h && q > p).length;
            }
        }
        return Object.values(t).map(r => {
            const pct = r.aw + r.al ? r.aw / (r.aw + r.al) : 0;
            const exp = Math.round(pct * r.g * 10) / 10;
            return { ...r, exp, luck: Math.round((r.w - exp) * 10) / 10, pf: Math.round(r.pf), pa: Math.round(r.pa) };
        }).sort((a, b) => b.luck - a.luck);
    }

    $: table = seasonTable(+season);
    $: bars = table.map(r => ({ label: nameOf(r.h), value: r.luck, note: `${r.w}-${r.l}, expected ${r.exp}`,
        highlight: ready && r.h === $myTeam, color: r.luck >= 0 ? '#27ae60' : '#e74c3c' }));
    const allTime = (() => {
        const m = {};
        for (const s of seasons) for (const r of seasonTable(s)) {
            const e = (m[r.h] ||= { h: r.h, luck: 0, n: 0 });
            e.luck += r.luck; e.n++;
        }
        return Object.values(m).map(e => ({ ...e, luck: Math.round(e.luck * 10) / 10 })).sort((a, b) => b.luck - a.luck);
    })();
    $: allBars = allTime.filter(e => current.has(e.h)).map(e => ({ label: nameOf(e.h), value: e.luck, note: `${e.n} seasons`,
        highlight: ready && e.h === $myTeam, color: e.luck >= 0 ? '#27ae60' : '#e74c3c' }));
    const seasonExtremes = (() => {
        const rows = seasons.filter(s => s !== site.season).flatMap(s => seasonTable(s).map(r => ({ ...r, season: s })));
        rows.sort((a, b) => b.luck - a.luck);
        return { lucky: rows.slice(0, 5), unlucky: rows.slice(-5).reverse() };
    })();
</script>

<div class="holder">
    <h1>Luck Meter</h1>
    <p class="sub">Your record depends on who you happened to play. "Expected wins" is what your record would be if every week you played all the other teams at once: beat 9 of 11 and that week is worth 0.82 wins. Luck is actual wins minus expected wins. Regular season only.</p>

    <div class="filters"><select bind:value={season}>{#each seasons as s}<option value={s}>{s}{s === site.season ? ' (so far)' : ''}</option>{/each}</select></div>
    <HBarChart items={bars} format={(v) => (v > 0 ? `+${v}` : `${v}`)} ariaLabel="Luck by team in {season}" />

    <div class="scroll">
        <table>
            <thead><tr><th>Manager</th><th class="num">Record</th><th class="num">Expected</th><th class="num">Luck</th><th class="num">Vs everyone</th><th class="num">Points for</th><th class="num">Points against</th></tr></thead>
            <tbody>
                {#each table as r}
                    <tr class:mine={ready && r.h === $myTeam}>
                        <td>{#if managerLink(r.h)}<a href={managerLink(r.h)}>{nameOf(r.h)}</a>{:else}{nameOf(r.h)}{/if}</td>
                        <td class="num">{r.w}-{r.l}</td><td class="num">{r.exp}</td>
                        <td class="num" class:pos={r.luck > 0} class:neg={r.luck < 0}>{r.luck > 0 ? '+' : ''}{r.luck}</td>
                        <td class="num">{r.aw}-{r.al}</td><td class="num">{r.pf}</td><td class="num">{r.pa}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <h2>Career luck, current managers</h2>
    <p class="note">Every season added up since {site.first_season}.</p>
    <HBarChart items={allBars} format={(v) => (v > 0 ? `+${v}` : `${v}`)} ariaLabel="Career luck" />

    <div class="two">
        <section>
            <h3>Luckiest seasons ever</h3>
            {#each seasonExtremes.lucky as r}<p>{r.season} <b>{nameOf(r.h)}</b> went {r.w}-{r.l}, expected {r.exp} <span class="pos">+{r.luck}</span></p>{/each}
        </section>
        <section>
            <h3>Unluckiest seasons ever</h3>
            {#each seasonExtremes.unlucky as r}<p>{r.season} <b>{nameOf(r.h)}</b> went {r.w}-{r.l}, expected {r.exp} <span class="neg">{r.luck}</span></p>{/each}
        </section>
    </div>
</div>

<style>
    .holder { max-width: 900px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { font-size: 1em; margin: 1em 0 0.3em; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .filters { text-align: center; margin: 0.8em 0; }
    select { padding: 0.3em 0.5em; font-size: 1em; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.9em; white-space: nowrap; }
    td a { color: inherit; font-weight: 600; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .pos { color: #2ecc71; font-weight: 700; }
    .neg { color: #e74c3c; font-weight: 700; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0 2em; }
    .two p { margin: 0.3em 0; font-size: 0.9em; }
</style>
