<script>
    // "His guys": the players a manager has drafted most, and the players who have
    // scored him the most points. Reads the same files as /players and /draft-grades.
    import { onMount } from 'svelte';
    import { site } from '$lib/utils/flpHistory';
    export let handle;

    let players = null, drafts = null, failed = false;
    onMount(async () => {
        try {
            const [p, d] = await Promise.all([
                fetch('/data/players.json').then(r => r.json()),
                fetch('/data/drafts.json').then(r => r.json()),
            ]);
            players = p; drafts = d;
        } catch (e) { failed = true; }
    });

    const r1 = (x) => Math.round(x * 10) / 10;

    // players.json: s = [season, handle, points started, starts, weeks rostered]
    $: scorers = !players ? [] : players.players
        .map(p => {
            const mine = p.s.filter(x => x[1] === handle);
            if (!mine.length) return null;
            return {
                n: p.n, pos: p.p,
                pts: r1(mine.reduce((t, x) => t + x[2], 0)),
                st: mine.reduce((t, x) => t + x[3], 0),
                seasons: mine.map(x => x[0]).sort(),
            };
        })
        .filter(Boolean)
        .sort((a, b) => b.pts - a.pts)
        .slice(0, 10);

    // drafts.json picks: [season, round, pick, manager, player, pos, value, live, draft, over]
    $: drafted = !drafts ? [] : Object.values(drafts.picks
        .filter(p => p[3] === handle)
        .reduce((m, p) => {
            const k = p[4];
            const e = (m[k] ||= { n: p[4], pos: p[5], times: 0, seasons: [], pts: 0, best: null });
            e.times++;
            e.seasons.push(p[0]);
            e.pts += p[6];
            if (!e.best || p[1] < e.best) e.best = p[1];
            return m;
        }, {}))
        .map(e => ({ ...e, pts: r1(e.pts), seasons: e.seasons.sort() }))
        .sort((a, b) => b.times - a.times || b.pts - a.pts)
        .filter(e => e.times > 1)
        .slice(0, 10);
    $: mostDraftedFallback = !drafts ? [] : drafts.picks.filter(p => p[3] === handle)
        .sort((a, b) => b[6] - a[6]).slice(0, 5)
        .map(p => ({ n: p[4], pos: p[5], times: 1, seasons: [p[0]], pts: r1(p[6]), best: p[1] }));
    $: draftList = drafted.length ? drafted : mostDraftedFallback;
</script>

{#if players || drafts}
    <section class="mp">
        <div class="two">
            <div>
                <h3>Players who scored the most for this team</h3>
                <p class="sub">Points while in the starting lineup, every season on record.</p>
                {#each scorers as p, i}
                    <div class="row"><span class="rk">{i + 1}</span><b>{p.n}</b><small>{p.pos} · {p.seasons.join(', ')}</small><em>{p.pts}</em></div>
                {:else}
                    <p class="sub">No lineup data yet.</p>
                {/each}
            </div>
            <div>
                <h3>{drafted.length ? 'Drafted again and again' : 'Best draft picks'}</h3>
                <p class="sub">{drafted.length ? 'Players taken in more than one draft, with the points they returned while started.' : 'The picks that returned the most points.'}</p>
                {#each draftList as p, i}
                    <div class="row"><span class="rk">{p.times > 1 ? `${p.times}×` : i + 1}</span><b>{p.n}</b><small>{p.pos} · {p.seasons.join(', ')} · first taken round {p.best}</small><em>{p.pts}</em></div>
                {:else}
                    <p class="sub">No drafts on record.</p>
                {/each}
            </div>
        </div>
        <p class="more"><a href="/players?who={handle}">All players</a> · <a href="/draft-grades">Draft grades</a></p>
    </section>
{:else if failed}
    <p class="sub err">Player history could not be loaded.</p>
{/if}

<style>
    .mp { max-width: 900px; margin: 0.5em auto 2em; padding: 0 1em; text-align: left; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0 2em; }
    h3 { margin: 1.2em 0 0.1em; font-size: 1em; }
    .sub { opacity: 0.7; font-size: 0.82em; margin: 0 0 0.4em; }
    .row { display: grid; grid-template-columns: 2.4em 1fr auto; grid-template-rows: auto auto; column-gap: 0.5em; padding: 0.25em 0; border-bottom: 1px solid rgba(127,127,127,0.18); font-size: 0.9em; }
    .rk { grid-row: span 2; opacity: 0.6; text-align: right; align-self: center; }
    .row small { grid-column: 2; opacity: 0.68; font-size: 0.85em; }
    .row em { grid-row: 1 / span 2; grid-column: 3; align-self: center; font-style: normal; font-weight: 700; font-variant-numeric: tabular-nums; }
    .more { margin-top: 1em; font-size: 0.9em; }
    .more a { color: #3498db; }
    .err { color: #e74c3c; }
</style>
