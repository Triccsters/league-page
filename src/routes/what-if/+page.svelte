<script>
    // Pick winners for the rest of the season and watch the playoff odds move.
    // The model is the same one behind the odds page: each team has a scoring
    // average and a spread, re-drawn per simulation. Games you pick are forced;
    // everything else is simulated.
    import { onMount } from 'svelte';
    import { nameOf, teamName, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import odds from '$lib/data/odds.json';

    const SIMS = 2500;

    let ready = false;
    onMount(() => { ready = true; });

    // handle -> forced winner for that game, keyed "week|a|b"
    let picks = {};
    let running = false;
    let result = null;

    const teams = odds.teams || [];
    const byHandle = Object.fromEntries(teams.map(t => [t.h, t]));
    const schedule = odds.schedule || {};
    const weeks = Object.keys(schedule).map(Number).sort((a, b) => a - b);
    const nPlayoff = odds.playoff_teams || 6;
    const sd = odds.sd || 25;

    const gameKey = (w, a, b) => `${w}|${a}|${b}`;
    const totalGames = weeks.reduce((n, w) => n + schedule[String(w)].length, 0);
    $: picked = Object.keys(picks).length;

    // box-muller, seeded well enough for this
    function gauss(mu, s) {
        let u = 0, v = 0;
        while (u === 0) u = Math.random();
        while (v === 0) v = Math.random();
        return mu + s * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    }

    function simulate() {
        const hs = teams.map(t => t.h);
        const made = Object.fromEntries(hs.map(h => [h, 0]));
        const byes = Object.fromEntries(hs.map(h => [h, 0]));
        const winSum = Object.fromEntries(hs.map(h => [h, 0]));

        for (let s = 0; s < SIMS; s++) {
            // each simulation gets its own view of how good every team really is
            const trueMu = {};
            for (const t of teams) trueMu[t.h] = gauss(t.mu, t.tau ?? 3);

            const w = {}, pf = {};
            for (const t of teams) { w[t.h] = t.w; pf[t.h] = t.pf; }

            for (const wk of weeks) {
                for (const [a, b] of schedule[String(wk)]) {
                    const forced = picks[gameKey(wk, a, b)];
                    let sa = gauss(trueMu[a], sd);
                    let sb = gauss(trueMu[b], sd);
                    if (forced === a && sb > sa) { const t = sa; sa = sb; sb = t; }
                    if (forced === b && sa > sb) { const t = sa; sa = sb; sb = t; }
                    pf[a] += sa; pf[b] += sb;
                    if (sa > sb) w[a]++; else if (sb > sa) w[b]++;
                }
            }
            const order = hs.slice().sort((x, y) => (w[y] - w[x]) || (pf[y] - pf[x]));
            for (let i = 0; i < nPlayoff && i < order.length; i++) made[order[i]]++;
            for (let i = 0; i < (odds.bye_teams || 0) && i < order.length; i++) byes[order[i]]++;
            for (const h of hs) winSum[h] += w[h];
        }

        return teams.map(t => ({
            h: t.h,
            base: t.playoff,
            playoff: Math.round((1000 * made[t.h]) / SIMS) / 10,
            bye: Math.round((1000 * byes[t.h]) / SIMS) / 10,
            wins: Math.round((10 * winSum[t.h]) / SIMS) / 10,
        })).sort((a, b) => b.playoff - a.playoff || b.wins - a.wins);
    }

    function run() {
        running = true;
        // let the button state paint before the loop blocks the thread
        setTimeout(() => {
            result = simulate();
            running = false;
        }, 20);
    }

    function pick(w, a, b, who) {
        const k = gameKey(w, a, b);
        if (picks[k] === who) {
            const { [k]: _drop, ...rest } = picks;
            picks = rest;
        } else {
            picks = { ...picks, [k]: who };
        }
        run();
    }

    function clearAll() {
        picks = {};
        run();
    }

    // pick every remaining game for one team, win or lose
    function sweep(handle, win) {
        const next = { ...picks };
        for (const w of weeks) {
            for (const [a, b] of schedule[String(w)]) {
                if (a !== handle && b !== handle) continue;
                const other = a === handle ? b : a;
                next[gameKey(w, a, b)] = win ? handle : other;
            }
        }
        picks = next;
        run();
    }

    onMount(run);

    const label = (h) => {
        const t = teamName(site.season, h);
        return t ? `${t} (${nameOf(h)})` : nameOf(h);
    };
    const delta = (r) => Math.round((r.playoff - r.base) * 10) / 10;
</script>

<div class="holder">
    <h1>What If</h1>
    <p class="sub">
        Pick winners for any of the {totalGames} games left and the playoff odds below re-run on the spot —
        {SIMS.toLocaleString()} simulations every time you click. Games you have not picked are still
        simulated from each team's scoring average and spread, the same model the
        <a href="/odds">playoff odds</a> page uses. Nothing here changes the real standings.
    </p>

    {#if !weeks.length}
        <p class="note">The regular season is finished, so there is nothing left to play with.</p>
    {:else}
        <div class="bar">
            <span>{picked} of {totalGames} games picked</span>
            <button onclick={clearAll} disabled={!picked}>Clear all</button>
            {#if ready && $myTeam && byHandle[$myTeam]}
                <button onclick={() => sweep($myTeam, true)}>Win out</button>
                <button onclick={() => sweep($myTeam, false)}>Lose out</button>
            {/if}
        </div>

        <div class="cols">
            <div class="games">
                {#each weeks as w}
                    <h3>Week {w}</h3>
                    {#each schedule[String(w)] as [a, b]}
                        {@const k = gameKey(w, a, b)}
                        <div class="game">
                            <button class="side" class:on={picks[k] === a} class:mine={ready && a === $myTeam}
                                onclick={() => pick(w, a, b, a)}>{nameOf(a)}</button>
                            <span class="v">v</span>
                            <button class="side" class:on={picks[k] === b} class:mine={ready && b === $myTeam}
                                onclick={() => pick(w, a, b, b)}>{nameOf(b)}</button>
                        </div>
                    {/each}
                {/each}
            </div>

            <div class="out">
                <h3>Playoff odds {running ? '…' : ''}</h3>
                <p class="note">Change against the published odds is in the last column.</p>
                {#if result}
                    <table>
                        <thead><tr><th>#</th><th>Manager</th><th class="num">Wins</th><th class="num">Playoffs</th><th class="num">Change</th></tr></thead>
                        <tbody>
                            {#each result as r, i}
                                <tr class:mine={ready && r.h === $myTeam} class:cut={i === nPlayoff}>
                                    <td class="num">{i + 1}</td>
                                    <td>{#if managerLink(r.h)}<a href={managerLink(r.h)}>{label(r.h)}</a>{:else}{label(r.h)}{/if}</td>
                                    <td class="num">{r.wins}</td>
                                    <td class="num"><b>{r.playoff}%</b></td>
                                    <td class="num" class:pos={delta(r) > 0.5} class:neg={delta(r) < -0.5}>
                                        {delta(r) > 0 ? '+' : ''}{delta(r)}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                    <p class="note">The line under {nPlayoff} is the playoff cut.</p>
                {:else}
                    <p class="note">Running…</p>
                {/if}
            </div>
        </div>
    {/if}
</div>

<style>
    .holder { max-width: 1050px; margin: 0 auto 3em; padding: 0 1em; text-align: left; }
    h1 { margin-bottom: 0.2em; }
    h3 { margin: 1em 0 0.3em; font-size: 0.95em; opacity: 0.8; }
    .sub { opacity: 0.75; font-size: 0.9em; max-width: 60em; }
    .sub a, td a { color: #3498db; }
    .note { opacity: 0.65; font-size: 0.8em; margin: 0.2em 0 0.6em; }
    .bar { display: flex; flex-wrap: wrap; gap: 0.5em; align-items: center; margin: 1em 0 0.2em; font-size: 0.85em; }
    .bar span { opacity: 0.75; margin-right: 0.3em; }
    button { font: inherit; cursor: pointer; border-radius: 6px; border: 1px solid rgba(127,127,127,0.4);
             background: transparent; color: inherit; padding: 0.25em 0.7em; font-size: 0.85em; }
    button:disabled { opacity: 0.4; cursor: default; }
    .cols { display: grid; grid-template-columns: minmax(260px, 1fr) minmax(300px, 1.3fr); gap: 0 2em; align-items: start; }
    .game { display: grid; grid-template-columns: 1fr auto 1fr; gap: 0.3em; align-items: center; margin-bottom: 0.3em; }
    .side { width: 100%; text-align: center; padding: 0.35em 0.3em; }
    .side.on { border-color: #27ae60; background: rgba(39,174,96,0.18); font-weight: 700; }
    .side.mine { border-style: dashed; }
    .v { opacity: 0.5; font-size: 0.75em; }
    table { border-collapse: collapse; width: 100%; font-size: 0.88em; }
    th, td { padding: 0.3em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.2); text-align: left; white-space: nowrap; }
    th { font-weight: 600; opacity: 0.75; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    tr.mine { background: rgba(52,152,219,0.14); }
    tr.cut { border-top: 2px solid rgba(231,76,60,0.7); }
    .pos { color: #27ae60; }
    .neg { color: #e74c3c; }
    @media (max-width: 760px) {
        .cols { grid-template-columns: 1fr; }
    }
</style>
