<script>
    // Every game this manager has played, a season at a time (T.J., 2026-11-13).
    import { games, nameOf, managerLink, teamName, slugFor } from '$lib/utils/flpHistory';
    export let handle;

    const REAL = ['Quarterfinal', 'Semifinal', 'Championship'];
    $: log = games.filter(g => (g.a === handle || g.b === handle) && g.pa != null && g.pb != null && (g.pa || g.pb))
        .map(g => {
            const home = g.a === handle;
            const pf = home ? g.pa : g.pb, pa = home ? g.pb : g.pa, opp = home ? g.b : g.a;
            const kind = !g.label ? (g.playoff ? 'Playoffs' : 'Regular season') : g.label;
            return { season: g.season, week: g.week, opp, pf, pa, res: pf > pa ? 'W' : pf < pa ? 'L' : 'T', kind,
                     tone: REAL.includes(g.label) ? 'po' : g.label ? 'con' : 'reg' };
        })
        .sort((x, y) => y.season - x.season || x.week - y.week);
    $: seasons = [...new Set(log.map(g => g.season))];
    let pick = null;
    $: if (pick === null || (pick !== 'all' && !seasons.includes(pick))) pick = seasons[0] ?? 'all';
    $: shown = pick === 'all' ? log : log.filter(g => g.season === pick);
    $: rec = shown.reduce((t, g) => { t[g.res]++; t.pf += g.pf; t.pa += g.pa; return t; }, { W: 0, L: 0, T: 0, pf: 0, pa: 0 });
    const r2 = (x) => (Math.round(x * 100) / 100).toFixed(2);
    const r1 = (x) => (Math.round(x * 10) / 10).toLocaleString('en-US');
</script>

{#if log.length}
    <section class="gl">
        <p class="eyebrow">Game log</p>
        <h3>Every game, {log.length} of them</h3>
        <div class="pick">
            {#each seasons as s}<button class:on={pick === s} on:click={() => (pick = s)}>{s}</button>{/each}
            <button class:on={pick === 'all'} on:click={() => (pick = 'all')}>All</button>
        </div>
        <p class="sub"><b>{rec.W}-{rec.L}{rec.T ? `-${rec.T}` : ''}</b> in {shown.length} game{shown.length === 1 ? '' : 's'}{pick === 'all' ? '' : ` in ${pick}`}, {r1(rec.pf)} points for and {r1(rec.pa)} against. Playoff and consolation games are marked.</p>
        <div class="scroll" class:tall={pick === 'all'}>
            <table>
                <thead><tr>{#if pick === 'all'}<th>Season</th>{/if}<th>Week</th><th>Opponent</th><th class="num">Score</th><th></th><th class="num">Margin</th><th>Game</th></tr></thead>
                <tbody>
                    {#each shown as g}
                        <tr>
                            {#if pick === 'all'}<td>{g.season}</td>{/if}
                            <td>{g.week}</td>
                            <td class="opp"><a href="/rivalries/{slugFor(handle, g.opp)}">{nameOf(g.opp)}</a>{#if teamName(g.season, g.opp) && teamName(g.season, g.opp) !== nameOf(g.opp)}<small>{teamName(g.season, g.opp)}</small>{/if}</td>
                            <td class="num">{r2(g.pf)} to {r2(g.pa)}</td>
                            <td><span class="res {g.res}">{g.res}</span></td>
                            <td class="num">{g.pf >= g.pa ? '+' : '-'}{r2(Math.abs(g.pf - g.pa))}</td>
                            <td><span class="kind {g.tone}">{g.kind}</span></td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    </section>
{/if}

<style>
    .gl { max-width: 900px; margin: 0.5em auto 2em; padding: 0 1em; text-align: left; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    h3 { margin: 0.1em 0 0.4em; font-size: 1.15em; }
    .sub { opacity: 0.8; font-size: 0.86em; margin: 0.5em 0; }
    .pick { display: flex; gap: 0.3em; flex-wrap: wrap; }
    .pick button { background: transparent; color: inherit; border: 1px solid rgba(127,127,127,0.45); border-radius: 14px; padding: 0.1em 0.7em; cursor: pointer; font-size: 0.88em; }
    .pick button.on { background: #3498db; border-color: #3498db; color: #fff; }
    .scroll { overflow-x: auto; }
    .scroll.tall { max-height: 34em; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
    th, td { padding: 0.35em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.18); text-align: left; white-space: nowrap; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .opp a { color: inherit; font-weight: 600; }
    .opp small { margin-left: 0.4em; opacity: 0.6; font-style: italic; }
    .res { display: inline-block; width: 1.6em; text-align: center; border-radius: 5px; font-weight: 800; font-size: 0.85em; color: #fff; }
    .res.W { background: #1e8449; } .res.L { background: #a93226; } .res.T { background: #566573; }
    .kind { font-size: 0.8em; opacity: 0.7; }
    .kind.po { opacity: 1; color: #1a1205; background: #f1c40f; border-radius: 5px; padding: 0.05em 0.45em; font-weight: 700; }
    .kind.con { opacity: 1; color: #fff; background: #566573; border-radius: 5px; padding: 0.05em 0.45em; }
</style>
