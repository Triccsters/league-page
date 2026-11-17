<script>
    import { onMount } from 'svelte';
    import { games, nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';
    import overviews from '$lib/data/overviews_extra.json';
    import all from '$lib/data/seasons.json';
    import nflAwards from '$lib/data/nfl_awards.json';

    export let data;
    $: year = data.year;

    // seasons.json is imported, so standings, bracket and awards render server-side.
    // The draft board and the trades are fetched: they are big, they live in
    // static/data already, and a missing one costs a section rather than the page.
    let drafts = null, trades = null, ready = false;
    onMount(async () => {
        ready = true;
        try { drafts = await fetch('/data/drafts.json').then((r) => r.json()); } catch { drafts = null; }
        try { trades = await fetch('/data/trades.json').then((r) => r.json()); } catch { trades = null; }
    });

    $: s = all?.seasons?.[String(year)] || null;
    // what the actual NFL handed out that year, looked up rather than recalled
    $: nfl = (nflAwards?.seasons || {})[String(year)] || null;
    $: prose = (overviews?.seasons || {})[String(year)] || null;
    $: proseParas = !prose ? [] : (Array.isArray(prose) ? prose : String(prose).split(/\n\n+/)).filter(Boolean);

    // every season on record, for the year strip
    $: years = all ? Object.keys(all.seasons).map(Number).sort((a, b) => b - a) : [];

    // --- matchups, straight from history.json ---------------------------
    $: seasonGames = games.filter((g) => g.season === year && g.pa != null && g.pb != null && (g.pa || g.pb));
    $: weeks = [...new Set(seasonGames.map((g) => g.week))].sort((a, b) => a - b);
    $: nameThatYear = (h) => (s?.standings || []).find((t) => t.h === h)?.name || nameOf(h);

    // --- draft board ----------------------------------------------------
    $: picks = !drafts ? [] : drafts.picks.filter((p) => p[0] === year);
    $: rounds = [...new Set(picks.map((p) => p[1]))].sort((a, b) => a - b);
    $: bestPicks = [...picks].filter((p) => p[9] != null).sort((a, b) => b[9] - a[9]).slice(0, 5);
    $: worstPicks = [...picks].filter((p) => p[9] != null).sort((a, b) => a[9] - b[9]).slice(0, 5);

    // --- trades ---------------------------------------------------------
    $: seasonTrades = !trades ? [] : (trades.trades || []).filter((t) => t.season === year);

    const REAL = ['Quarterfinal', 'Semifinal', 'Championship', '3rd place'];
    $: realRounds = !s ? [] : REAL.filter((r) => s.bracket[r]).map((r) => [r, s.bracket[r]]);
    $: placeRounds = !s ? [] : Object.entries(s.bracket)
        .filter(([k]) => !REAL.includes(k))
        .sort((a, b) => (a[1][0]?.week || 0) - (b[1][0]?.week || 0));

    const n1 = (x) => (x == null ? '' : (Math.round(x * 100) / 100).toLocaleString());
    const rec = (t) => `${t.w}-${t.l}${t.t ? `-${t.t}` : ''}`;
    const sign = (x) => (x > 0 ? `+${n1(x)}` : n1(x));
</script>

<svelte:head><title>{year} | {site.league_name}</title></svelte:head>

<div class="holder">
    <nav class="years">
        {#each years as y}
            <a href="/season/{y}" class:on={y === year}>{y}</a>
        {/each}
    </nav>

    <h1>{year}</h1>

    {#if !s}
        <p class="sub">No games are on record for {year}.
            {#if years.length}The league's seasons run {Math.min(...years)} to {Math.max(...years)}.{/if}</p>
    {:else}
        <!-- ── the headline ─────────────────────────────────────────── -->
        {#if s.champion}
            <div class="crown">
                <span class="trophy">🏆</span>
                <div>
                    <b>{nameOf(s.champion)}</b> won it
                    {#if s.title_game}
                        , {n1(Math.max(s.title_game.pa, s.title_game.pb))}–{n1(Math.min(s.title_game.pa, s.title_game.pb))}
                        over {nameOf(s.runner_up)}
                    {/if}
                    {#if s.third}<small>{nameOf(s.third)} took third.</small>{/if}
                </div>
            </div>
        {:else if s.current}
            <p class="sub">This season is still being played — {s.format.reg_weeks} weeks in. Everything below is the season so far.</p>
        {/if}

        <p class="note">
            {s.format.teams} teams · {s.format.reg_weeks}-week regular season
            {#if s.format.playoff_weeks.length}· playoffs in week{s.format.playoff_weeks.length > 1 ? 's' : ''} {s.format.playoff_weeks.join(' and ')}{/if}
            · {s.format.scoring}
            {#if s.format.era === 'yahoo'}· played on Yahoo{/if}
        </p>

        {#if proseParas.length}
            <section class="yr">
                <h2>{year} in review</h2>
                {#each proseParas as p}<p>{p}</p>{/each}
            </section>
        {/if}

        <!-- ── awards ──────────────────────────────────────────────── -->
        <section>
            <h2>The {year} awards</h2>
            <p class="note">Every one of these compares the teams of {year} against each other, under
                that season's scoring and schedule, so unlike the all-time records they need no era
                adjustment. Teams whose manager was never identified win them like anyone else.</p>
            {#if nfl}
                <div class="nfl">
                    <span class="nt">In the actual NFL that year</span>
                    {#if nfl.note}<p class="nnote">{nfl.note}</p>{/if}
                    <div class="nrow">
                        {#if nfl.mvp}
                            <div><b>MVP</b> {nfl.mvp.n} <small>{nfl.mvp.pos} · {nfl.mvp.team}</small></div>
                        {/if}
                        {#if nfl.oroy}
                            <div><b>Offensive Rookie of the Year</b> {nfl.oroy.n}
                                <small>{nfl.oroy.pos} · {nfl.oroy.team}</small></div>
                        {/if}
                    </div>
                </div>
            {/if}

            <div class="awards">
                {#each s.awards as a}
                    <div class="aw" class:mine={ready && a.h === $myTeam}>
                        <span class="at">{a.title}</span>
                        <b>
                            {#if managerLink(a.h)}<a href={managerLink(a.h)}>{nameOf(a.h)}</a>{:else}{nameOf(a.h)}{/if}
                            <YourTeamBadge handle={a.h} size="small" />
                        </b>
                        <span class="ad">{a.detail}</span>
                    </div>
                {/each}
            </div>
        </section>

        <!-- ── standings ───────────────────────────────────────────── -->
        <section>
            <h2>Final standings</h2>
            <p class="note">Regular season only. All-play is the record this team would have had
                against every other team every week, so the gap between the two is schedule luck.</p>
            <div class="scroll">
                <table>
                    <thead><tr>
                        <th>#</th><th>Manager</th><th>Team that year</th><th>W-L</th>
                        <th class="num">PF</th><th class="num">PA</th><th class="num">PF rank</th>
                        <th>All-play</th><th>Finished</th>
                    </tr></thead>
                    <tbody>
                        {#each s.standings as t}
                            <tr class:mine={ready && t.h === $myTeam} class:champ={t.title}>
                                <td>{t.seed}</td>
                                <td>{#if managerLink(t.h)}<a href={managerLink(t.h)}>{nameOf(t.h)}</a>{:else}{nameOf(t.h)}{/if}
                                    {#if t.title}<span class="tag">champion</span>{/if}
                                    <YourTeamBadge handle={t.h} size="small" /></td>
                                <td class="tn">{t.name}</td>
                                <td>{rec(t)}</td>
                                <td class="num">{n1(t.pf)}</td>
                                <td class="num">{n1(t.pa)}</td>
                                <td class="num">{t.pf_rank}</td>
                                <td>{t.allplay[0]}-{t.allplay[1]}
                                    <small class:good={t.luck > 0} class:bad={t.luck < 0}>{sign(Math.round(t.luck * 1000) / 10)}%</small></td>
                                <td class="po">{t.playoff.length ? t.playoff.join(', ') : '—'}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- ── the title game, player by player ────────────────────── -->
        {#if s.title_lineups && s.title_game}
            <section>
                <h2>The title game, player by player</h2>
                <p class="note">Both starting lineups from the final. Championship week is when NFL
                    teams with a playoff seed already locked start resting people, so a star with
                    almost nothing next to his name is often a real story rather than a bad day.</p>
                <div class="lineups">
                    {#each [s.champion, s.runner_up] as h}
                        {@const L = s.title_lineups[h]}
                        {#if L}
                            <div class="lu" class:won={h === s.champion}>
                                <h3>{nameOf(h)} <em>{n1(L.total)}</em>
                                    {#if h === s.champion}<span class="tag">won</span>{/if}</h3>
                                {#each L.starters as p}
                                    <div class="st" class:zero={p.pts <= 2}>
                                        <span class="sp {p.pos}">{p.pos || '—'}</span>
                                        <b>{p.n}</b><em>{n1(p.pts)}</em>
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    {/each}
                </div>
            </section>
        {/if}

        <!-- ── bracket ─────────────────────────────────────────────── -->
        {#if realRounds.length}
            <section>
                <h2>Playoff bracket</h2>
                <div class="rounds">
                    {#each realRounds as [label, gs]}
                        <div class="rnd">
                            <h3>{label}</h3>
                            {#each gs as g}
                                <div class="pg">
                                    <div class="side" class:won={g.winner === g.a}>
                                        <span>{nameOf(g.a)}</span><em>{n1(g.pa)}</em></div>
                                    <div class="side" class:won={g.winner === g.b}>
                                        <span>{nameOf(g.b)}</span><em>{n1(g.pb)}</em></div>
                                    <small>week {g.week}</small>
                                </div>
                            {/each}
                        </div>
                    {/each}
                </div>
                {#if placeRounds.length}
                    <details>
                        <summary>Placement and consolation games ({placeRounds.reduce((n, r) => n + r[1].length, 0)})</summary>
                        <div class="rounds">
                            {#each placeRounds as [label, gs]}
                                <div class="rnd">
                                    <h3>{label}</h3>
                                    {#each gs as g}
                                        <div class="pg">
                                            <div class="side" class:won={g.winner === g.a}><span>{nameOf(g.a)}</span><em>{n1(g.pa)}</em></div>
                                            <div class="side" class:won={g.winner === g.b}><span>{nameOf(g.b)}</span><em>{n1(g.pb)}</em></div>
                                            <small>week {g.week}</small>
                                        </div>
                                    {/each}
                                </div>
                            {/each}
                        </div>
                    </details>
                {/if}
            </section>
        {/if}

        <!-- ── every matchup ───────────────────────────────────────── -->
        <section>
            <h2>Every matchup</h2>
            <p class="note">{seasonGames.length} games. Team names are the ones used that season.</p>
            {#each weeks as wk}
                <details open={wk === weeks[weeks.length - 1]}>
                    <summary>Week {wk}
                        {#if seasonGames.find((g) => g.week === wk && g.playoff)}<span class="tag">playoffs</span>{/if}
                    </summary>
                    <div class="board">
                        {#each seasonGames.filter((g) => g.week === wk) as g}
                            <div class="mg">
                                <div class="side" class:won={g.pa > g.pb}>
                                    <span>{nameThatYear(g.a)}</span><em>{n1(g.pa)}</em></div>
                                <div class="side" class:won={g.pb > g.pa}>
                                    <span>{nameThatYear(g.b)}</span><em>{n1(g.pb)}</em></div>
                                {#if g.label}<small>{g.label}</small>{/if}
                            </div>
                        {/each}
                    </div>
                </details>
            {/each}
        </section>

        <!-- ── draft ───────────────────────────────────────────────── -->
        {#if picks.length}
            <section>
                <h2>The {year} draft</h2>
                <p class="note">{picks.length} picks over {rounds.length} rounds. "Over" is what the player
                    returned against what a pick at that spot usually returns, so it rates the pick rather
                    than the player.</p>
                <div class="two">
                    <div>
                        <h3>Best picks</h3>
                        {#each bestPicks as p}
                            <div class="pk"><span class="sl">{p[1]}.{p[2]}</span><b>{p[4]}</b>
                                <small>{p[5]} · {nameOf(p[3])}</small><em class="good">{sign(p[9])}</em></div>
                        {/each}
                    </div>
                    <div>
                        <h3>Worst picks</h3>
                        {#each worstPicks as p}
                            <div class="pk"><span class="sl">{p[1]}.{p[2]}</span><b>{p[4]}</b>
                                <small>{p[5]} · {nameOf(p[3])}</small><em class="bad">{sign(p[9])}</em></div>
                        {/each}
                    </div>
                </div>
                <details>
                    <summary>The full board</summary>
                    {#each rounds as rd}
                        <div class="rdrow">
                            <span class="rdn">R{rd}</span>
                            <div class="rdpicks">
                                {#each picks.filter((p) => p[1] === rd).sort((a, b) => a[2] - b[2]) as p}
                                    <div class="cell {p[5]}" class:mine={ready && p[3] === $myTeam}>
                                        <b>{p[4]}</b><small>{p[5] || '—'} · {nameOf(p[3])}</small>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/each}
                </details>
            </section>
        {/if}

        <!-- ── trades ──────────────────────────────────────────────── -->
        <section>
            <h2>Trades</h2>
            {#if !trades}
                <p class="sub">Loading…</p>
            {:else if !seasonTrades.length}
                <p class="sub">No trades were made in {year}.</p>
            {:else}
                <p class="note">{seasonTrades.length} trade{seasonTrades.length > 1 ? 's' : ''}. The winner is
                    whoever got more rest-of-season points out of it.</p>
                {#each seasonTrades as t}
                    <div class="tr">
                        <small class="wk">week {t.week}</small>
                        <div class="sides">
                            {#each Object.entries(t.sides) as [h, side]}
                                <div class="tside" class:won={t.winner === h}>
                                    <b>{nameOf(h)} got</b>
                                    {#each side.got || [] as p}
                                        <span class="got">{p.n}
                                            <small>{p.p} · {n1(p.pts)} pts in {p.st} start{p.st === 1 ? '' : 's'}</small>
                                        </span>
                                    {/each}
                                    {#each side.picks || [] as pk}
                                        <span class="got">{typeof pk === 'string' ? pk : JSON.stringify(pk)}</span>
                                    {/each}
                                    {#if !((side.got || []).length + (side.picks || []).length)}
                                        <span class="got"><small>nothing on record</small></span>
                                    {/if}
                                    <span class="tval">{n1(side.value)} points after the trade</span>
                                </div>
                            {/each}
                        </div>
                        {#if t.margin}<small class="mg2">{nameOf(t.winner)} came out ahead by {n1(t.margin)}</small>{/if}
                    </div>
                {/each}
            {/if}
        </section>

        <p class="foot">
            Built from the league's own game record. See also
            <a href="/record-book">the record book</a>, <a href="/all-time">the all-time table</a>
            and <a href="/hall-of-fame">the Hall of Fame</a>.
        </p>
    {/if}
</div>

<style>
    .holder { max-width: 1040px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin: 0.2em 0 0.1em; font-size: 2.4em; }
    h2 { margin: 1.6em 0 0.3em; font-size: 1.25em; }
    h3 { margin: 0 0 0.4em; font-size: 0.95em; opacity: 0.85; }
    .sub, .note { opacity: 0.78; font-size: 0.9em; line-height: 1.5; margin: 0.2em 0 0.8em; }
    .note { text-align: center; }
    .err { color: #e74c3c; text-align: center; }
    section { margin-bottom: 0.6em; }

    .years { display: flex; flex-wrap: wrap; gap: 0.3em; justify-content: center; margin-bottom: 0.6em; }
    .years a { font-size: 0.82em; padding: 0.2em 0.5em; border-radius: 6px; color: inherit;
        border: 1px solid rgba(127,127,127,0.3); text-decoration: none; font-variant-numeric: tabular-nums; }
    .years a.on { background: #3498db; color: #ffffff; border-color: #3498db; font-weight: 700; }

    .crown { display: flex; align-items: center; justify-content: center; gap: 0.6em;
        background: rgba(241, 196, 15, 0.14); border: 1px solid rgba(241, 196, 15, 0.5);
        border-radius: 12px; padding: 0.7em 1em; margin: 0.4em 0 0.6em; }
    .crown .trophy { font-size: 1.7em; }
    .crown b { font-size: 1.05em; }
    .crown small { display: block; opacity: 0.8; }

    .yr p { line-height: 1.6; margin: 0 0 0.7em; }

    .nfl { border: 1px solid rgba(52, 152, 219, 0.45); background: rgba(52, 152, 219, 0.1);
        border-radius: 10px; padding: 0.6em 0.8em; margin-bottom: 0.7em; }
    .nt { display: block; font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.07em;
        opacity: 0.75; margin-bottom: 0.3em; }
    .nrow { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.5em; }
    .nnote { margin: 0 0 0.5em; line-height: 1.55; font-size: 0.93em; }
    .nrow b { display: block; font-size: 0.8em; opacity: 0.8; font-weight: 700; }
    .nrow small { display: block; opacity: 0.7; font-size: 0.82em; }

    .awards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 0.6em; }
    .aw { border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; padding: 0.6em 0.75em; }
    .aw.mine { border-color: #27ae60; background: rgba(39, 174, 96, 0.12); }
    .at { display: block; font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.07em; opacity: 0.68; }
    .aw b { display: block; margin: 0.15em 0; }
    .aw b a { color: #3498db; }
    .ad { font-size: 0.86em; opacity: 0.82; line-height: 1.4; }

    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; white-space: nowrap; }
    th { font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    td a { color: #3498db; }
    tr.mine td { background: rgba(39, 174, 96, 0.14); }
    tr.champ td { background: rgba(241, 196, 15, 0.12); }
    .tn { opacity: 0.8; max-width: 16em; overflow: hidden; text-overflow: ellipsis; }
    .po { font-size: 0.85em; opacity: 0.8; white-space: normal; }
    td small { font-size: 0.82em; opacity: 0.7; margin-left: 0.3em; }
    .good { color: #27ae60; } .bad { color: #e74c3c; }
    .tag { font-size: 0.68em; text-transform: uppercase; letter-spacing: 0.06em;
        background: rgba(241,196,15,0.25); padding: 0.1em 0.4em; border-radius: 4px; margin-left: 0.3em; }

    .lineups { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 0.8em; }
    .lu { border: 1px solid rgba(127,127,127,0.28); border-radius: 11px; padding: 0.6em 0.75em; }
    .lu.won { border-color: rgba(241,196,15,0.55); background: rgba(241,196,15,0.08); }
    .lu h3 { display: flex; align-items: baseline; gap: 0.4em; font-size: 1em; margin-bottom: 0.45em; opacity: 1; }
    .lu h3 em { margin-left: auto; font-style: normal; font-weight: 800; font-variant-numeric: tabular-nums; }
    .st { display: grid; grid-template-columns: 2.9em 1fr auto; gap: 0.45em; align-items: baseline;
        padding: 0.2em 0; border-bottom: 1px solid rgba(127,127,127,0.15); }
    .st b { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
    .st em { font-style: normal; font-variant-numeric: tabular-nums; }
    .st.zero b, .st.zero em { color: #e74c3c; }
    .sp { font-size: 0.66em; font-weight: 800; letter-spacing: 0.04em; text-align: center;
        border-radius: 3px; padding: 0.15em 0; background: rgba(127,127,127,0.2); }
    .sp.QB { background: #c0392b; color: #fff; } .sp.RB { background: #1e8449; color: #fff; }
    .sp.WR { background: #2471a3; color: #fff; } .sp.TE { background: #ca6f1e; color: #fff; }
    .sp.K { background: #7d3c98; color: #fff; } .sp.DEF { background: #566573; color: #fff; }

    .rounds { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 0.7em; }
    .rnd { min-width: 0; }
    .pg, .mg { border: 1px solid rgba(127,127,127,0.28); border-radius: 9px; padding: 0.4em 0.55em; margin-bottom: 0.4em; }
    .side { display: flex; justify-content: space-between; gap: 0.5em; padding: 0.1em 0; opacity: 0.6; }
    .side.won { opacity: 1; font-weight: 700; }
    .side span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .side em { font-style: normal; font-variant-numeric: tabular-nums; }
    .pg small, .mg small { display: block; font-size: 0.74em; opacity: 0.6; margin-top: 0.15em; }

    .board { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 0.5em; }
    details { margin: 0.3em 0 0.6em; }
    summary { cursor: pointer; font-weight: 700; font-size: 0.92em; padding: 0.25em 0; }

    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1em; }
    .pk { display: grid; grid-template-columns: 2.6em 1fr auto; gap: 0.4em; align-items: baseline;
        padding: 0.25em 0; border-bottom: 1px solid rgba(127,127,127,0.18); }
    .pk .sl { font-size: 0.8em; opacity: 0.65; font-variant-numeric: tabular-nums; }
    .pk small { display: block; font-size: 0.78em; opacity: 0.7; }
    .pk em { font-style: normal; font-weight: 700; font-variant-numeric: tabular-nums; }

    .rdrow { display: grid; grid-template-columns: 2.2em 1fr; gap: 0.4em; margin-bottom: 0.3em; align-items: center; }
    .rdn { font-weight: 700; opacity: 0.6; font-size: 0.82em; }
    .rdpicks { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 2px; min-width: 0; }
    .cell { border-radius: 4px; padding: 0.2em 0.35em; font-size: 0.72em; min-width: 0;
        background: rgba(127,127,127,0.14); }
    .cell b { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cell small { opacity: 0.75; font-size: 0.9em; overflow: hidden; text-overflow: ellipsis;
        white-space: nowrap; display: block; }
    .cell.QB { background: #c0392b; color: #ffffff; } .cell.RB { background: #1e8449; color: #ffffff; }
    .cell.WR { background: #2471a3; color: #ffffff; } .cell.TE { background: #ca6f1e; color: #ffffff; }
    .cell.K { background: #7d3c98; color: #ffffff; } .cell.DEF { background: #566573; color: #ffffff; }
    .cell.mine { outline: 2px solid #27ae60; }

    .tr { border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; padding: 0.5em 0.7em; margin-bottom: 0.5em; }
    .wk { font-size: 0.74em; opacity: 0.65; text-transform: uppercase; letter-spacing: 0.06em; }
    .sides { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.5em; margin-top: 0.2em; }
    .tside { font-size: 0.9em; border-left: 3px solid rgba(127,127,127,0.3); padding-left: 0.6em; }
    .tside.won { border-left-color: #27ae60; }
    .tside.won b { color: #27ae60; }
    .tside b { display: block; margin-bottom: 0.15em; }
    .got { display: block; opacity: 0.9; font-size: 0.95em; line-height: 1.3; margin-bottom: 0.15em; }
    .got small { display: block; opacity: 0.65; font-size: 0.85em; }
    .tval { display: block; margin-top: 0.3em; font-size: 0.82em; opacity: 0.7;
        font-variant-numeric: tabular-nums; }
    .mg2 { display: block; margin-top: 0.3em; font-size: 0.8em; opacity: 0.8; }

    .foot { margin-top: 2em; font-size: 0.85em; opacity: 0.7; text-align: center; line-height: 1.6; }
    .foot a { color: #3498db; }

    @media (max-width: 560px) {
        h1 { font-size: 1.9em; }
        .years a { font-size: 0.76em; padding: 0.15em 0.4em; }
    }
</style>
