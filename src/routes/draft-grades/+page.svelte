<script>
    import { onMount } from 'svelte';
    import { nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    let data = null, error = '', ready = false, pick = null;
    onMount(async () => {
        ready = true;
        try {
            data = await fetch('/data/drafts.json').then(r => r.json());
            const done = Object.keys(data.grades).filter(k => !k.startsWith(String(site.season)));
            pick = done[done.length - 1] || Object.keys(data.grades).pop();
        } catch (e) { error = 'Could not load the draft history.'; }
    });

    // picks: [season, round, pick, manager, player, pos, value, live, draft, over]
    const P = (p) => ({ season: p[0], rnd: p[1], no: p[2], h: p[3], n: p[4], pos: p[5], val: p[6], live: p[7], draft: p[8], over: p[9] });
    $: all = data ? data.picks.map(P) : [];
    $: done = all.filter(p => !p.live);
    $: keys = data ? Object.keys(data.grades).sort().reverse() : [];
    $: keyOf = (p) => `${p.season}${p.draft ? ' ' + p.draft : ''}`;
    $: inDraft = all.filter(p => keyOf(p) === pick);
    $: live = inDraft.some(p => p.live);
    $: gradeRows = pick && data ? Object.entries(data.grades[pick]).map(([h, g]) => ({ h, ...g })).sort((a, b) => a.rank - b.rank) : [];
    $: steals = [...inDraft].sort((a, b) => b.over - a.over).slice(0, 8);
    $: busts = [...inDraft].filter(p => p.rnd <= 6).sort((a, b) => a.over - b.over).slice(0, 8);
    $: bestEver = [...done].sort((a, b) => b.over - a.over).slice(0, 10);
    $: worstEver = [...done].filter(p => p.rnd <= 4).sort((a, b) => a.over - b.over).slice(0, 10);
    $: drafterBars = data ? Object.entries(data.managers).map(([h, m]) => ({ label: nameOf(h), value: m.avg, note: `${m.hit}% hits, ${m.n} picks`, highlight: ready && h === $myTeam }))
        .sort((a, b) => b.value - a.value) : [];
    const gradeColor = (g) => g.startsWith('A') ? '#27ae60' : g.startsWith('B') ? '#2980b9' : g.startsWith('C') ? '#7f8c8d' : g.startsWith('D') ? '#e67e22' : '#c0392b';
    const who = (h) => managerLink(h);
</script>

<div class="holder">
    <h1>Draft Grades</h1>
    {#if data}
        <p class="sub">Each pick is judged by what it returned: the points that player scored <b>in the drafting manager's starting lineup</b>{data.dynasty ? ' in every season he stayed on that roster' : ' that season'}, compared with the average pick in the same round. Positive means the pick beat its round.</p>

        <h2>Grade a draft</h2>
        <div class="filters">
            <select bind:value={pick}>{#each keys as k}<option value={k}>{k}</option>{/each}</select>
            {#if live}<span class="live">{site.season} is in progress, so these grades will move every week.</span>{/if}
        </div>
        <div class="grades">
            {#each gradeRows as g}
                <div class="grade" class:mine={ready && g.h === $myTeam}>
                    <span class="letter" style="background:{gradeColor(g.grade)}">{g.grade}</span>
                    <span>{#if who(g.h)}<a href={who(g.h)}>{nameOf(g.h)}</a>{:else}{nameOf(g.h)}{/if}</span>
                    <small>{g.over > 0 ? '+' : ''}{g.over} vs round average</small>
                </div>
            {/each}
        </div>
        <div class="two">
            <section>
                <h3>Best picks of this draft</h3>
                {#each steals as p}<div class="pk"><span>R{p.rnd}.{p.no}</span><b>{p.n}</b><small>{p.pos} · {nameOf(p.h)}</small><em class="pos">+{p.over}</em></div>{/each}
            </section>
            <section>
                <h3>Biggest misses (first 6 rounds)</h3>
                {#each busts as p}<div class="pk"><span>R{p.rnd}.{p.no}</span><b>{p.n}</b><small>{p.pos} · {nameOf(p.h)}</small><em class="neg">{p.over}</em></div>{/each}
            </section>
        </div>

        <h2>Best drafters, all time</h2>
        <p class="note">Average points each pick returned above or below its round. Finished seasons only.</p>
        <HBarChart items={drafterBars} format={(v) => (v > 0 ? `+${v}` : `${v}`)} ariaLabel="Average value over round by manager" />

        <div class="two">
            <section>
                <h3>Best picks ever</h3>
                {#each bestEver as p}<div class="pk"><span>{p.season} R{p.rnd}</span><b>{p.n}</b><small>{p.pos} · {nameOf(p.h)} · {p.val} pts</small><em class="pos">+{p.over}</em></div>{/each}
            </section>
            <section>
                <h3>Worst early picks ever (rounds 1–4)</h3>
                {#each worstEver as p}<div class="pk"><span>{p.season} R{p.rnd}</span><b>{p.n}</b><small>{p.pos} · {nameOf(p.h)} · {p.val} pts</small><em class="neg">{p.over}</em></div>{/each}
            </section>
        </div>
    {:else if error}
        <p class="sub">{error}</p>
    {:else}
        <p class="sub">Loading drafts…</p>
    {/if}
</div>

<style>
    .holder { max-width: 960px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { font-size: 1em; margin: 1em 0 0.3em; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .filters { display: flex; gap: 0.8em; align-items: center; flex-wrap: wrap; }
    select { padding: 0.3em 0.5em; font-size: 1em; }
    .live { font-style: italic; opacity: 0.75; font-size: 0.9em; }
    .grades { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.5em; margin: 0.8em 0; }
    .grade { display: grid; grid-template-columns: 2.6em 1fr; grid-template-rows: auto auto; column-gap: 0.6em; align-items: center; border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.4em 0.6em; }
    .grade.mine { border-color: #27ae60; background: rgba(39,174,96,0.12); }
    .letter { grid-row: span 2; color: #fff; font-weight: 800; text-align: center; border-radius: 6px; padding: 0.35em 0; }
    .grade a { color: inherit; font-weight: 600; }
    .grade small { opacity: 0.7; font-size: 0.78em; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0 2em; }
    .pk { display: grid; grid-template-columns: 5.2em 1fr auto; grid-template-rows: auto auto; column-gap: 0.5em; padding: 0.3em 0; border-bottom: 1px solid rgba(127,127,127,0.18); font-size: 0.9em; }
    .pk span { grid-row: span 2; opacity: 0.65; font-size: 0.85em; }
    .pk small { grid-column: 2; opacity: 0.7; }
    .pk em { grid-row: 1 / span 2; grid-column: 3; align-self: center; font-style: normal; font-weight: 700; font-variant-numeric: tabular-nums; }
    .pos { color: #2ecc71; }
    .neg { color: #e74c3c; }
</style>
