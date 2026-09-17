<script>
    import { onMount } from 'svelte';
    import odds from '$lib/data/odds.json';
    import { nameOf, teamName, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';

    let ready = false;
    onMount(() => { ready = true; });
    const mine = (h) => ready && h === $myTeam;

    // trend chart: chance to make the playoffs after each week
    const weeks = Object.keys(odds.history || {}).map(Number).sort((a, b) => a - b);
    const COLORS = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#e84393', '#95a5a6', '#34495e', '#fd79a8', '#00cec9'];
    const W = 640, H = 260, L = 34, R = 10, T = 10, B = 26;
    const px = (i) => L + (i * (W - L - R)) / Math.max(1, weeks.length - 1);
    const py = (v) => T + (H - T - B) * (1 - v / 100);
    const lines = odds.teams.map((t, i) => ({
        h: t.h, color: COLORS[i % COLORS.length],
        d: weeks.map((w, j) => `${j ? 'L' : 'M'}${px(j).toFixed(1)},${py(odds.history[w][t.h] ?? 0).toFixed(1)}`).join(' '),
    }));
    let focus = null;

    $: titleBars = odds.teams.map(t => ({ label: nameOf(t.h), value: t.title, highlight: mine(t.h) }))
        .sort((a, b) => b.value - a.value);
    const pct = (v) => (v >= 99.95 ? '>99.9' : v > 0 && v < 0.1 ? '<0.1' : v.toFixed(1)) + '%';
</script>

<div class="holder">
    <h1>Playoff Odds</h1>
    <p class="sub">After week {odds.through_week} of {odds.season}. {odds.sims.toLocaleString()} simulated finishes of the {odds.remaining_weeks.length} regular-season weeks left.
        Top {odds.playoff_teams} make the playoffs{odds.playoff_teams >= 6 ? ', top 2 get a bye' : ''}{odds.median ? ', and every week also counts a game against the league median' : ''}.</p>

    <div class="scroll">
        <table>
            <thead><tr><th>Team</th><th>W-L</th><th class="num">Proj. wins</th><th class="bar">Playoffs</th>{#if odds.playoff_teams >= 6}<th class="num">Bye</th>{/if}<th class="num">#1 seed</th><th class="num">Title</th><th class="num">Last place</th></tr></thead>
            <tbody>
                {#each odds.teams as t}
                    <tr class:mine={mine(t.h)}>
                        <td><b>{nameOf(t.h)}</b><YourTeamBadge handle={t.h} size="small" />
                            {#if teamName(site.season, t.h) && teamName(site.season, t.h) !== nameOf(t.h)}<small>{teamName(site.season, t.h)}</small>{/if}</td>
                        <td>{t.w}-{t.l}</td>
                        <td class="num">{t.proj_w}</td>
                        <td class="bar"><div class="meter"><span style="width:{t.playoff}%"></span><em>{pct(t.playoff)}</em></div></td>
                        {#if odds.playoff_teams >= 6}<td class="num">{pct(t.bye)}</td>{/if}
                        <td class="num">{pct(t.seed1)}</td>
                        <td class="num">{pct(t.title)}</td>
                        <td class="num">{pct(t.last)}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <h2>Championship chances</h2>
    <HBarChart items={titleBars} format={(v) => `${v}%`} ariaLabel="Chance to win the title" />

    {#if weeks.length >= 2}
        <h2>How the playoff race has moved</h2>
        <p class="note">Tap a name to follow one team.</p>
        <svg viewBox="0 0 {W} {H}" role="img" aria-label="Playoff odds by week">
            {#each [0, 25, 50, 75, 100] as v}
                <line x1={L} x2={W - R} y1={py(v)} y2={py(v)} class="grid" />
                <text x={L - 5} y={py(v) + 4} class="tick" text-anchor="end">{v}</text>
            {/each}
            {#each weeks as w, j}<text x={px(j)} y={H - 8} class="tick" text-anchor="middle">W{w}</text>{/each}
            {#each lines as ln}
                <path d={ln.d} stroke={ln.color} class="ln" class:dim={(focus && focus !== ln.h) || (!focus && ready && $myTeam && ln.h !== $myTeam)} />
            {/each}
        </svg>
        <div class="keys">
            {#each lines as ln}
                <button class:on={focus === ln.h} on:click={() => (focus = focus === ln.h ? null : ln.h)}><i style="background:{ln.color}"></i>{nameOf(ln.h)}</button>
            {/each}
        </div>
    {:else}
        <p class="note">A week-by-week chart of the race appears once there are two weeks of odds.</p>
    {/if}

    <details class="how">
        <summary>How are these odds worked out?</summary>
        <p>Each team gets an expected weekly score: its average this season, pulled toward its scoring last season and the league average while there are only a few games to go on. The site then plays out every remaining regular-season game {odds.sims.toLocaleString()} times with realistic week-to-week swings (a typical score varies by about {odds.sd} points), ranks the teams by wins and then points, and plays out the bracket. Each run also redraws how good every team really is, which keeps early-season odds from getting too confident.</p>
        <p>It does not look at rosters, injuries or trades, so a team that just traded for a star will be underrated until the points show up. Updated every Tuesday.</p>
    </details>
</div>

<style>
    .holder { max-width: 960px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    .sub, .note { text-align: center; opacity: 0.75; font-size: 0.92em; }
    .scroll { overflow-x: auto; margin-top: 1em; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.92em; white-space: nowrap; }
    td small { display: block; opacity: 0.65; font-style: italic; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .bar { min-width: 160px; }
    .meter { position: relative; height: 1.4em; background: rgba(127,127,127,0.18); border-radius: 4px; overflow: hidden; }
    .meter span { position: absolute; left: 0; top: 0; bottom: 0; background: #3498db; }
    .meter em { position: relative; font-style: normal; font-weight: 700; padding-left: 0.4em; line-height: 1.4em; color: #fff; text-shadow: 0 0 3px #000; }
    svg { width: 100%; height: auto; }
    .grid { stroke: currentColor; opacity: 0.12; }
    .tick { fill: currentColor; opacity: 0.7; font-size: 11px; }
    .ln { fill: none; stroke-width: 2.5; transition: opacity 0.2s; }
    .ln.dim { opacity: 0.15; }
    .keys { display: flex; flex-wrap: wrap; gap: 0.3em; justify-content: center; }
    .keys button { background: transparent; color: inherit; border: 1px solid rgba(127,127,127,0.4); border-radius: 14px; padding: 0.15em 0.6em; cursor: pointer; font-size: 0.85em; }
    .keys button.on { border-color: #3498db; }
    .keys i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 0.3em; }
    .how { margin: 2em 0 1em; padding: 0.6em 1em; border: 1px solid rgba(127,127,127,0.35); border-radius: 8px; line-height: 1.5; font-size: 0.92em; }
    .how summary { cursor: pointer; font-weight: 600; color: #3498db; }
</style>
