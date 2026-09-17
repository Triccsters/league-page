<script>
    // Record book computed from every game in history.json, all platforms.
    import { onMount } from 'svelte';
    import { games, nameOf, site, hasYahoo, teamName, managerLink, managers } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });

    const N = 10;
    let era = 'all';
    const REAL = new Set(['Quarterfinal', 'Semifinal', 'Championship']);
    const r2 = (x) => Math.round(x * 100) / 100;

    $: pool = games.filter(g => era === 'all' || g.era === era);
    // one row per team-game
    $: sides = pool.flatMap(g => [
        { season: g.season, week: g.week, era: g.era, h: g.a, pts: g.pa, opp: g.b, opts: g.pb, label: g.label, playoff: g.playoff },
        { season: g.season, week: g.week, era: g.era, h: g.b, pts: g.pb, opp: g.a, opts: g.pa, label: g.label, playoff: g.playoff },
    ]);
    // consolation games are not counted as records; real playoff rounds are
    $: counted = sides.filter(s => !s.playoff || REAL.has(s.label));
    $: decided = pool.filter(g => g.pa !== g.pb && (!g.playoff || REAL.has(g.label))).map(g => {
        const aw = g.pa > g.pb;
        return { season: g.season, week: g.week, label: g.label, h: aw ? g.a : g.b, pts: Math.max(g.pa, g.pb),
                 opp: aw ? g.b : g.a, opts: Math.min(g.pa, g.pb), margin: r2(Math.abs(g.pa - g.pb)) };
    });

    const top = (arr, key, dir = -1) => [...arr].sort((x, y) => dir * (x[key] - y[key])).slice(0, N);

    $: highWeek = top(counted, 'pts');
    $: lowWeek = top(counted.filter(s => s.pts > 0), 'pts', 1);
    $: blowouts = top(decided, 'margin');
    $: closest = top(decided, 'margin', 1);
    $: bestLoss = top(counted.filter(s => s.pts < s.opts), 'pts');
    $: worstWin = top(counted.filter(s => s.pts > s.opts), 'pts', 1);

    // season totals: regular season only, and only seasons that are over
    $: seasons = (() => {
        const m = {};
        for (const s of sides) {
            if (s.playoff || s.season === site.season) continue;
            const k = s.season + '|' + s.h;
            const t = (m[k] ||= { season: s.season, h: s.h, pts: 0, g: 0, w: 0, l: 0 });
            t.pts += s.pts; t.g++;
            if (s.pts > s.opts) t.w++; else if (s.pts < s.opts) t.l++;
        }
        return Object.values(m).map(t => ({ ...t, pts: r2(t.pts), ppg: r2(t.pts / t.g) }));
    })();
    $: highSeason = top(seasons, 'ppg');
    $: lowSeason = top(seasons, 'ppg', 1);
    $: mostWins = [...seasons].sort((x, y) => y.w - x.w || y.ppg - x.ppg).slice(0, N);

    // streaks across seasons, regular season only
    $: streaks = (() => {
        const by = {};
        for (const s of [...sides].filter(s => !s.playoff).sort((x, y) => x.season - y.season || x.week - y.week)) (by[s.h] ||= []).push(s);
        const win = [], lose = [];
        for (const [h, list] of Object.entries(by)) {
            let cur = null, n = 0, start = null;
            const close = (e) => { if (cur && n >= 3) (cur === 'W' ? win : lose).push({ h, n, from: start, to: e }); };
            let prev = null;
            for (const s of list) {
                const r = s.pts > s.opts ? 'W' : s.pts < s.opts ? 'L' : 'T';
                if (r === cur) n++;
                else { close(prev); cur = r; n = 1; start = s; }
                prev = s;
            }
            close(prev);
        }
        const srt = (a) => a.sort((x, y) => y.n - x.n).slice(0, N);
        return { win: srt(win), lose: srt(lose) };
    })();

    const when = (s) => `${s.season} ${s.label && s.label !== 'Consolation' ? s.label : 'W' + s.week}`;
    const span = (x) => `${x.from.season} W${x.from.week} to ${x.to.season} W${x.to.week}`;
    const mine = (h) => ready && h === $myTeam;
</script>

<svelte:head><title>Record Book | {site.league_name}</title></svelte:head>

{#snippet who(h, season)}
    {@const t = season != null ? teamName(season, h) : null}
    <span class="who">
        {#if managerLink(h)}<a href={managerLink(h)}>{nameOf(h)}</a>{:else}<span>{nameOf(h)}</span>{/if}
        {#if managers[h]?.hidden}<small class="tag">manager hidden</small>{/if}
        {#if t && t !== nameOf(h) && !managers[h]?.hidden}<small class="team">{t}</small>{/if}
    </span>
{/snippet}

<div class="holder">
    <h1>📜 Record Book</h1>
    <p class="sub">Every record is computed from all {games.length.toLocaleString()} games since {site.first_season}. Consolation games don't count. Season records use the regular season only and leave out {site.season} until it's over. Names link to manager pages.</p>
    {#if hasYahoo}
        <div class="filter">
            {#each [['all', 'All seasons'], ['yahoo', `Yahoo (${site.yahoo_years[0]}–${site.yahoo_years[1]})`], ['sleeper', `Sleeper (${site.sleeper_from}–now)`]] as [k, l]}
                <button class:on={era === k} on:click={() => (era = k)}>{l}</button>
            {/each}
        </div>
        <p class="note">Scoring changed over the years (standard scoring before 2018, half PPR since), so older seasons score lower across the board.</p>
    {/if}

    <div class="grid">
        <section>
            <h2>💯 Highest single-week scores</h2>
            {#each highWeek as r, i}
                <div class="row" class:mine={mine(r.h)} class:live={r.season === site.season}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.pts}</span><span class="meta">{when(r)}<br />vs {nameOf(r.opp)}</span></div>
            {/each}
        </section>
        <section>
            <h2>🐢 Lowest single-week scores</h2>
            {#each lowWeek as r, i}
                <div class="row" class:mine={mine(r.h)} class:live={r.season === site.season}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.pts}</span><span class="meta">{when(r)}<br />vs {nameOf(r.opp)}</span></div>
            {/each}
        </section>
        <section>
            <h2>💥 Biggest blowouts</h2>
            {#each blowouts as r, i}
                <div class="row" class:mine={mine(r.h)} class:live={r.season === site.season}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">+{r.margin}</span><span class="meta">{when(r)}<br />over {nameOf(r.opp)}, {r.pts}–{r.opts}</span></div>
            {/each}
        </section>
        <section>
            <h2>🪒 Closest games</h2>
            {#each closest as r, i}
                <div class="row" class:mine={mine(r.h)} class:live={r.season === site.season}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">+{r.margin}</span><span class="meta">{when(r)}<br />over {nameOf(r.opp)}, {r.pts}–{r.opts}</span></div>
            {/each}
        </section>
        <section>
            <h2>😤 Most points in a loss</h2>
            {#each bestLoss as r, i}
                <div class="row" class:mine={mine(r.h)} class:live={r.season === site.season}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.pts}</span><span class="meta">{when(r)}<br />lost to {nameOf(r.opp)}, {r.opts}</span></div>
            {/each}
        </section>
        <section>
            <h2>🍀 Fewest points in a win</h2>
            {#each worstWin as r, i}
                <div class="row" class:mine={mine(r.h)} class:live={r.season === site.season}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.pts}</span><span class="meta">{when(r)}<br />beat {nameOf(r.opp)}, {r.opts}</span></div>
            {/each}
        </section>
        <section>
            <h2>📈 Best seasons, points per game</h2>
            {#each highSeason as r, i}
                <div class="row" class:mine={mine(r.h)}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.ppg}</span><span class="meta">{r.season}, {r.w}-{r.l}<br />{r.pts} in {r.g} games</span></div>
            {/each}
        </section>
        <section>
            <h2>📉 Worst seasons, points per game</h2>
            {#each lowSeason as r, i}
                <div class="row" class:mine={mine(r.h)}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.ppg}</span><span class="meta">{r.season}, {r.w}-{r.l}<br />{r.pts} in {r.g} games</span></div>
            {/each}
        </section>
        <section>
            <h2>🏅 Most wins in a season</h2>
            {#each mostWins as r, i}
                <div class="row" class:mine={mine(r.h)}><span class="rk">{i + 1}</span>{@render who(r.h, r.season)}<span class="val">{r.w}-{r.l}</span><span class="meta">{r.season}<br />{r.ppg} per game</span></div>
            {/each}
        </section>
        <section>
            <h2>🔥 Longest winning streaks</h2>
            {#each streaks.win as r, i}
                <div class="row" class:mine={mine(r.h)}><span class="rk">{i + 1}</span>{@render who(r.h, null)}<span class="val">{r.n}</span><span class="meta">{span(r)}</span></div>
            {/each}
        </section>
        <section>
            <h2>🧊 Longest losing streaks</h2>
            {#each streaks.lose as r, i}
                <div class="row" class:mine={mine(r.h)}><span class="rk">{i + 1}</span>{@render who(r.h, null)}<span class="val">{r.n}</span><span class="meta">{span(r)}</span></div>
            {/each}
        </section>
    </div>
    <p class="note">Streaks count regular-season games in a row and carry over from one season to the next. Rows in green are from the {site.season} season.</p>
</div>

<style>
    .holder { max-width: 1150px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub, .note { text-align: center; opacity: 0.75; font-size: 0.92em; }
    .filter { display: flex; justify-content: center; gap: 0.5em; flex-wrap: wrap; margin: 1em 0 0.3em; }
    .filter button { padding: 0.35em 0.9em; border-radius: 16px; border: 1px solid rgba(127,127,127,0.5); background: transparent; color: inherit; cursor: pointer; }
    .filter button.on { background: #3498db; border-color: #3498db; color: #fff; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 0 2em; }
    h2 { font-size: 1.1em; margin: 1.5em 0 0.3em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.25em; }
    .row { display: grid; grid-template-columns: 1.6em 1fr auto 8.5em; gap: 0.6em; align-items: center; padding: 0.35em 0.3em; border-bottom: 1px solid rgba(127,127,127,0.18); font-size: 0.9em; }
    .row.mine { background: rgba(39, 174, 96, 0.15); }
    .row.live { box-shadow: inset 3px 0 0 #2ecc71; }
    .rk { opacity: 0.6; text-align: right; }
    .who { display: flex; flex-direction: column; min-width: 0; }
    .who a { color: inherit; font-weight: 600; text-decoration: none; }
    .who a:hover { color: #3498db; }
    .who > span { font-weight: 600; }
    .team { font-style: italic; opacity: 0.7; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .tag { font-size: 0.72em; opacity: 0.7; text-transform: uppercase; }
    .val { font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
    .meta { font-size: 0.8em; opacity: 0.7; text-align: right; line-height: 1.3; }
</style>
