<script>
    // The ESPN data that only a league hosted on ESPN has (League Bound):
    // projected finish vs draft day, moves per team, failed claims, trade
    // attempts and vetoes, ESPN's free-agent pool and ownership trends, and
    // matchup strength by position. Data: src/lib/data/espn.json, written by
    // scripts/espn_extras.py. On every other site the file doesn't exist and
    // this renders nothing.
    import { onMount } from 'svelte';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import HBarChart from '$lib/Charts/HBarChart.svelte';

    const files = import.meta.glob('/src/lib/data/espn.json', { eager: true, import: 'default' });
    const d = Object.values(files)[0] || null;
    let ready = false;
    onMount(() => { ready = true; });

    const POSN = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
    let defPos = 'QB';
    let faPos = 'ALL';
    const sign = (v) => (v > 0 ? `+${v}` : `${v}`);
    $: rankRows = d ? [...d.teams].filter((t) => t.draft_rank && t.now_rank)
        .map((t) => ({ ...t, delta: t.draft_rank - t.now_rank }))
        .sort((a, b) => b.delta - a.delta) : [];
    $: rankBars = rankRows.map((t) => ({
        label: nameOf(t.h), value: t.delta, note: `${t.draft_rank} on draft day, ${t.now_rank} now`,
        color: t.delta >= 0 ? '#27ae60' : '#e74c3c', highlight: ready && t.h === $myTeam,
    }));
    $: nextBars = d ? [...d.teams].sort((a, b) => b.proj_next - a.proj_next).map((t) => ({
        label: nameOf(t.h), value: t.proj_next, highlight: ready && t.h === $myTeam,
    })) : [];
    $: moves = d ? [...d.teams].sort((a, b) => (b.moves.acquisitions + b.moves.drops) - (a.moves.acquisitions + a.moves.drops)) : [];
    $: shownTrades = d ? d.trade_attempts.filter((a) => a.status === 'executed' || a.status === 'vetoed') : [];
    $: fa = d ? d.free_agents.filter((p) => faPos === 'ALL' || p.p === faPos).slice(0, 15) : [];
    $: def = d && d.defense[defPos] ? d.defense[defPos] : [];
    const link = (h) => managerLink(h);
</script>

{#if d}
    <section class="espn">
        <h2>From ESPN</h2>
        <p class="note">This league lives on ESPN, so it gets the extra data ESPN keeps on every league. Updated every Tuesday; next up is week {d.next_week}.</p>

        <h3>Who's beating their draft</h3>
        <p class="note">ESPN projected every team's finish on draft day and keeps re-projecting it. Bars show places gained or lost since the draft.</p>
        <HBarChart items={rankBars} format={sign} ariaLabel="Projected finish, draft day vs now" />

        <h3>ESPN's projection for week {d.next_week}</h3>
        <p class="note">Each team's current starting lineup, using ESPN's projections in this league's scoring.</p>
        <HBarChart items={nextBars} ariaLabel="ESPN projected points next week" />

        {#if d.upside && d.upside.length}
            <h3>Biggest boom potential in week {d.next_week}</h3>
            <p class="note">ESPN's projection and its ceiling for each player. The bigger the gap, the more room for a boom.</p>
            <div class="scroll">
                <table>
                    <thead><tr><th>Player</th><th>Team</th><th class="num">Proj</th><th class="num">Ceiling</th><th class="num">Room</th></tr></thead>
                    <tbody>
                        {#each d.upside as p}<tr class:mine={ready && p.h === $myTeam}><td><b>{p.n}</b> <span class="muted">{p.p}{p.start ? '' : ', bench'}</span></td><td>{nameOf(p.h)}</td><td class="num">{p.proj}</td><td class="num">{p.ceil}</td><td class="num pos">+{(p.ceil - p.proj).toFixed(1)}</td></tr>{/each}
                    </tbody>
                </table>
            </div>
        {/if}

        <h3>Busiest on the wire</h3>
        <div class="scroll">
            <table>
                <thead><tr><th>Team</th><th class="num">Adds</th><th class="num">Drops</th><th class="num">Lineup moves</th><th class="num">IR moves</th><th class="num">Trades</th><th class="num">Offers turned down</th><th class="num">Waiver order</th></tr></thead>
                <tbody>
                    {#each moves as t}
                        <tr class:mine={ready && t.h === $myTeam}>
                            <td>{#if link(t.h)}<a href={link(t.h)}>{nameOf(t.h)}</a>{:else}{nameOf(t.h)}{/if}</td>
                            <td class="num">{t.moves.acquisitions}</td><td class="num">{t.moves.drops}</td>
                            <td class="num">{t.moves.moveToActive}</td><td class="num">{t.moves.moveToIR}</td>
                            <td class="num">{t.moves.trades}</td><td class="num">{d.declines[t.h] || 0}</td>
                            <td class="num">{t.waiver_rank}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        {#if shownTrades.length}
            <h3>Trades, including the ones that didn't happen</h3>
            {#each shownTrades as a}
                <p class="trade"><span class="tag" class:bad={a.status === 'vetoed'}>{a.status}</span> <span class="muted">{a.date}</span>
                    {#each a.sides as s, i}{i ? ' · ' : ' '}<b>{nameOf(s.h)}</b> gets {s.gets.join(', ')}{/each}</p>
            {/each}
        {/if}

        {#if d.claims_failed.length}
            <h3>Claims that didn't go through</h3>
            <p class="note">Waiver claims that lost to a team higher in the order, or were cancelled before they ran.</p>
            <div class="chips">
                {#each d.claims_failed as c}
                    <span class="chip" class:mine={ready && c.h === $myTeam}>Wk {c.w} · <b>{nameOf(c.h)}</b> · {c.n} <span class="muted">{c.p}, {c.why}</span></span>
                {/each}
            </div>
        {/if}

        <h3>The free-agent pool</h3>
        <p class="note">Unrostered here, sorted by how many ESPN leagues roster them. "Proj" is ESPN's week {d.next_week} projection in this league's scoring.</p>
        <div class="filters">{#each ['ALL', ...POSN] as p}<button class:on={faPos === p} on:click={() => (faPos = p)}>{p}</button>{/each}</div>
        <div class="scroll">
            <table>
                <thead><tr><th>Player</th><th>Pos</th><th>Team</th><th class="num">% owned</th><th class="num">Change</th><th class="num">Proj</th><th>Status</th></tr></thead>
                <tbody>
                    {#each fa as p}<tr><td>{p.n}</td><td>{p.p}</td><td>{p.t}</td><td class="num">{p.own}</td><td class="num" class:pos={p.chg > 0} class:neg={p.chg < 0}>{sign(p.chg)}</td><td class="num">{p.proj ?? '–'}</td><td>{p.status}</td></tr>{/each}
                </tbody>
            </table>
        </div>

        <div class="two">
            <section>
                <h3>Rising across ESPN</h3>
                {#each d.risers.slice(0, 8) as p}<p><b>{p.n}</b> <span class="muted">{p.p}, {nameOf(p.h)}</span> <span class="pos">{sign(p.chg)}%</span> <span class="muted">{p.own}% owned</span></p>{/each}
            </section>
            <section>
                <h3>Falling across ESPN</h3>
                {#each d.fallers.slice(0, 8) as p}<p><b>{p.n}</b> <span class="muted">{p.p}, {nameOf(p.h)}</span> <span class="neg">{sign(p.chg)}%</span> <span class="muted">{p.own}% owned</span></p>{/each}
            </section>
        </div>

        <h3>Matchups by position</h3>
        <p class="note">Average fantasy points this league's scoring gives up to each position, by opponent, this season. Rank 1 is the toughest matchup.</p>
        <div class="filters">{#each POSN as p}<button class:on={defPos === p} on:click={() => (defPos = p)}>{p}</button>{/each}</div>
        <div class="two">
            <section>
                <h3>Toughest for a {defPos}</h3>
                {#each def.slice(0, 8) as r}<p><b>{r.rank}.</b> {r.t} <span class="muted">{r.avg} a game</span></p>{/each}
            </section>
            <section>
                <h3>Softest for a {defPos}</h3>
                {#each [...def].reverse().slice(0, 8) as r}<p><b>{r.rank}.</b> {r.t} <span class="muted">{r.avg} a game</span></p>{/each}
            </section>
        </div>
        <p class="note small">Source: {d.source}. ESPN's written player outlooks are left out on purpose.</p>
    </section>
{/if}

<style>
    .espn { margin-top: 2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { font-size: 1em; margin: 1.4em 0 0.3em; }
    .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; }
    .small { font-size: 0.8em; margin-top: 1.5em; }
    .scroll { overflow-x: auto; margin-top: 0.6em; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.9em; white-space: nowrap; }
    td a { color: inherit; font-weight: 600; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .pos { color: #2ecc71; font-weight: 700; }
    .neg { color: #e74c3c; font-weight: 700; }
    .muted { opacity: 0.7; font-size: 0.9em; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2em; }
    @media (max-width: 640px) { .two { grid-template-columns: 1fr; } }
    .two p { margin: 0.25em 0; font-size: 0.92em; }
    .trade { margin: 0.35em 0; font-size: 0.92em; line-height: 1.5; }
    .tag { font-size: 0.72em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #fff; background: #1e8449; border-radius: 4px; padding: 0.15em 0.45em; }
    .tag.bad { background: #c0392b; }
    .chips { display: flex; flex-wrap: wrap; gap: 0.35em; }
    .chip { font-size: 0.82em; border: 1px solid rgba(127,127,127,0.4); border-radius: 999px; padding: 0.15em 0.6em; }
    .chip.mine { border-color: #27ae60; background: rgba(39,174,96,0.12); }
    .filters { display: flex; flex-wrap: wrap; gap: 0.3em; justify-content: center; margin: 0.4em 0; }
    .filters button { font: inherit; font-size: 0.8em; cursor: pointer; border: 1px solid rgba(127,127,127,0.45); background: transparent; color: inherit; border-radius: 6px; padding: 0.15em 0.55em; }
    .filters button.on { background: #27ae60; border-color: #27ae60; color: #fff; }
</style>
