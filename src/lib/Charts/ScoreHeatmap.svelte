<script>
    // Every team's score, every week of one season. Cell colour = how that score
    // ranked league-wide that week (green top, red bottom). W/L shown in the corner.
    import { onMount } from 'svelte';
    import { games, nameOf } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    export let season;

    let ready = false;
    onMount(() => { ready = true; });

    const list = games.filter(g => g.season === season && !g.playoff);
    const weeks = [...new Set(list.map(g => g.week))].sort((a, b) => a - b);
    const cell = {};          // handle -> week -> { pts, won, rank, of }
    for (const w of weeks) {
        const wk = list.filter(g => g.week === w);
        const scores = wk.flatMap(g => [g.pa, g.pb]).sort((a, b) => b - a);
        for (const g of wk) {
            for (const [me, mp, op] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
                (cell[me] ||= {})[w] = { pts: mp, won: mp > op, rank: scores.indexOf(mp) + 1, of: scores.length };
            }
        }
    }
    const rows = Object.keys(cell).map(h => {
        const cs = Object.values(cell[h]);
        return { h, wins: cs.filter(c => c.won).length, pf: cs.reduce((s, c) => s + c.pts, 0) };
    }).sort((a, b) => b.wins - a.wins || b.pf - a.pf);

    // Bright, dark-mode-safe ramp from red (worst) through slate to green (best)
    const colour = (c) => {
        const t = c.of > 1 ? (c.of - c.rank) / (c.of - 1) : 0.5;
        if (t >= 0.5) {
            const k = (t - 0.5) * 2;
            return `rgb(${Math.round(60 - 21 * k)}, ${Math.round(70 + 104 * k)}, ${Math.round(80 + 16 * k)})`;
        }
        const k = (0.5 - t) * 2;
        return `rgb(${Math.round(60 + 132 * k)}, ${Math.round(70 - 13 * k)}, ${Math.round(80 - 37 * k)})`;
    };
</script>

{#if weeks.length}
<div class="wrap">
    <table>
        <thead>
            <tr><th>Team</th>{#each weeks as w}<th>W{w}</th>{/each}<th class="num">PF</th></tr>
        </thead>
        <tbody>
            {#each rows as r}
                <tr class:mine={ready && $myTeam === r.h}>
                    <td class="name">{nameOf(r.h)}</td>
                    {#each weeks as w}
                        {@const c = cell[r.h][w]}
                        {#if c}
                            <td class="c" style="background:{colour(c)}" title="{nameOf(r.h)} week {w}: {c.pts} ({c.won ? 'won' : 'lost'}), #{c.rank} of {c.of}">
                                {Math.round(c.pts)}<i>{c.won ? 'W' : 'L'}</i>
                            </td>
                        {:else}<td></td>{/if}
                    {/each}
                    <td class="num">{r.pf.toFixed(1)}</td>
                </tr>
            {/each}
        </tbody>
    </table>
    <p class="key"><span class="sw" style="background:rgb(39,174,96)"></span>highest score that week <span class="sw" style="background:rgb(192,57,43)"></span>lowest · W/L is the matchup result</p>
</div>
{/if}

<style>
    .wrap { overflow-x: auto; margin: 0.5em 0 1.5em; }
    table { border-collapse: separate; border-spacing: 3px; font-size: 0.85em; }
    th { font-weight: 600; opacity: 0.8; padding: 0.2em 0.3em; }
    td.name { white-space: nowrap; padding-right: 0.6em; }
    td.c { color: #fff; text-align: center; min-width: 2.8em; padding: 0.35em 0.3em; border-radius: 4px; position: relative; font-variant-numeric: tabular-nums; }
    td.c i { position: absolute; top: 1px; right: 3px; font-size: 0.65em; font-style: normal; opacity: 0.85; }
    .num { text-align: right; padding-left: 0.6em; }
    tr.mine td.name { color: #27ae60; font-weight: 700; }
    tr.mine td.c { outline: 2px solid #27ae60; }
    .key { font-size: 0.8em; opacity: 0.75; }
    .sw { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: middle; margin: 0 0.3em 0 0.8em; }
</style>
