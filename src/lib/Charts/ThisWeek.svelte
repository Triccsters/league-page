<script>
    // This week in league history: what happened in the same week of earlier seasons.
    import { onMount } from 'svelte';
    import { games, nameOf, managerLink, teamName, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });

    const reg = games.filter(g => !g.playoff);
    // the week the league is on now: one past the last week with scores
    const played = reg.filter(g => g.season === site.season).map(g => g.week);
    const week = Math.max(1, (played.length ? Math.max(...played) : 0) + 1);

    const past = reg.filter(g => g.week === week && g.season < site.season);
    const r2 = (v) => Math.round(v * 100) / 100;

    const best = past.length
        ? past.reduce((b, g) => {
            const [h, p] = g.pa >= g.pb ? [g.a, g.pa] : [g.b, g.pb];
            return !b || p > b.p ? { h, p, season: g.season } : b;
        }, null)
        : null;

    const closest = past.length
        ? past.reduce((b, g) => {
            const d = Math.abs(g.pa - g.pb);
            return !b || d < b.d ? { d, g } : b;
        }, null)
        : null;

    const blowout = past.length
        ? past.reduce((b, g) => {
            const d = Math.abs(g.pa - g.pb);
            return !b || d > b.d ? { d, g } : b;
        }, null)
        : null;

    const winnerOf = (g) => (g.pa >= g.pb ? g.a : g.b);
    const loserOf = (g) => (g.pa >= g.pb ? g.b : g.a);
    const hi = (g) => Math.max(g.pa, g.pb);
    const lo = (g) => Math.min(g.pa, g.pb);

    // the viewer's own history in this week
    $: mine = !ready || !$myTeam ? [] : past
        .filter(g => g.a === $myTeam || g.b === $myTeam)
        .map(g => {
            const me = g.a === $myTeam ? g : { ...g, a: g.b, pa: g.pb, b: g.a, pb: g.pa };
            return { season: g.season, mp: me.pa, op: me.pb, them: me.b, won: me.pa > me.pb };
        })
        .sort((a, b) => b.season - a.season)
        .slice(0, 4);

    $: record = mine.length ? `${mine.filter(m => m.won).length}-${mine.filter(m => !m.won).length}` : null;

    const link = (h) => managerLink(h);
</script>

{#if past.length}
    <section class="tw">
        <h3>This week in league history</h3>
        <p class="sub">Week {week}, going back through {past.length} games in earlier seasons.</p>

        <ul>
            {#if best}
                <li>
                    <span class="em">🔥</span>
                    <span>
                        Highest week {week} score: <b>{r2(best.p)}</b> by
                        {#if link(best.h)}<a href={link(best.h)}>{nameOf(best.h)}</a>{:else}{nameOf(best.h)}{/if}
                        in {best.season}{#if teamName(best.season, best.h)} as {teamName(best.season, best.h)}{/if}.
                    </span>
                </li>
            {/if}
            {#if closest}
                <li>
                    <span class="em">😬</span>
                    <span>
                        Closest week {week} game: {nameOf(winnerOf(closest.g))} beat {nameOf(loserOf(closest.g))}
                        {r2(hi(closest.g))} to {r2(lo(closest.g))} in {closest.g.season} — {r2(closest.d)} points.
                    </span>
                </li>
            {/if}
            {#if blowout}
                <li>
                    <span class="em">💀</span>
                    <span>
                        Worst week {week} beating: {nameOf(winnerOf(blowout.g))} over {nameOf(loserOf(blowout.g))}
                        {r2(hi(blowout.g))} to {r2(lo(blowout.g))} in {blowout.g.season}.
                    </span>
                </li>
            {/if}
        </ul>

        {#if mine.length}
            <h4>Your week {week}s <small>({record})</small></h4>
            <ul class="mine">
                {#each mine as m}
                    <li>
                        <span class="yr">{m.season}</span>
                        <span class:won={m.won} class:lost={!m.won}>{m.won ? 'W' : 'L'}</span>
                        <span>{r2(m.mp)} to {r2(m.op)} against {nameOf(m.them)}</span>
                    </li>
                {/each}
            </ul>
        {/if}
    </section>
{/if}

<style>
    .tw { border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; padding: 0.8em 1em;
          margin: 1em auto; max-width: 900px; text-align: left; }
    h3 { margin: 0 0 0.1em; font-size: 1em; }
    h4 { margin: 0.9em 0 0.2em; font-size: 0.9em; }
    h4 small { opacity: 0.6; font-weight: 400; }
    .sub { opacity: 0.65; font-size: 0.8em; margin: 0 0 0.6em; }
    ul { list-style: none; margin: 0; padding: 0; }
    li { display: grid; grid-template-columns: 1.6em 1fr; gap: 0.4em; padding: 0.25em 0; font-size: 0.88em;
         line-height: 1.35; }
    .em { font-size: 1.05em; }
    ul.mine li { grid-template-columns: 3em 1.4em 1fr; align-items: baseline; }
    .yr { opacity: 0.65; font-variant-numeric: tabular-nums; }
    .won { color: #27ae60; font-weight: 700; }
    .lost { color: #e74c3c; font-weight: 700; }
    a { color: #3498db; }
</style>
