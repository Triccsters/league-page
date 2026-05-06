<script>
    export let data;
    const { allTimeData } = data;
</script>

<style>
    .holder {
        max-width: 900px;
        margin: 0 auto;
        padding: 1.5em 1em;
    }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub { color: var(--g777, #777); text-align: center; font-size: 0.95em; margin-bottom: 2em; }
    h2 {
        margin-top: 2em;
        margin-bottom: 0.5em;
        font-size: 1.2em;
        border-bottom: 2px solid var(--ddd, #ddd);
        padding-bottom: 0.3em;
    }
    .narrative {
        background: var(--fff, rgba(255,255,255,0.04));
        border-left: 3px solid #999;
        padding: 1em 1.5em;
        margin: 1.5em 0;
        font-size: 1em;
        line-height: 1.6;
        border-radius: 4px;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5em; }
    th, td { padding: 0.5em; border-bottom: 1px solid var(--ddd, #ddd); text-align: left; font-size: 0.95em; }
    th { background: var(--fff, #fafafa); font-weight: 600; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .runner-up td { background: rgba(192, 192, 192, 0.18); }
</style>

<div class="holder">
    <h1>🏈 T.J.'s FL Players Career</h1>
    <p class="sub">15 seasons in the league — 0 championships, 3 runner-ups, lots of being so close.</p>

    {#await allTimeData}
        <p class="sub">Loading...</p>
    {:then d}
        <div class="narrative">
            <strong>The narrative</strong>: T.J. has played in the FL Players league since at least 2010 (15+ seasons including 2011 in basic training). Made the championship game three times — <strong>2014, 2019, and 2020</strong> — and lost all three. Every other year ended with a regular-season finish in the bottom half of the league.
            <br><br>
            <em>Pattern</em>: when he's good, he's elite enough to make the finals. When he's not, he's bottom-tier. No middle ground.
        </div>

        <h2>Yahoo era (2010–2020)</h2>
        <table>
            <thead>
                <tr>
                    <th>Season</th>
                    <th>Team name</th>
                    <th class="num">W-L-T</th>
                    <th>Finish</th>
                </tr>
            </thead>
            <tbody>
                {#each d.tj_career_yahoo as s}
                    <tr class:runner-up={s.finished === 'Runner-up'}>
                        <td><strong>{s.season}</strong></td>
                        <td>{s.team}</td>
                        <td class="num">
                            {#if s.wins != null}
                                {s.wins}-{s.losses}{s.ties ? `-${s.ties}` : ''}
                            {:else}—{/if}
                        </td>
                        <td>{s.finished}</td>
                    </tr>
                {/each}
            </tbody>
        </table>

        <h2>Sleeper era (2021–present)</h2>
        {#if d.tj_career_sleeper}
            <table>
                <thead>
                    <tr>
                        <th>Manager</th>
                        <th class="num">Seasons</th>
                        <th class="num">W-L-T</th>
                        <th class="num">Win %</th>
                        <th class="num">Points For</th>
                        <th class="num">🏆</th>
                        <th class="num">2nd</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="top1">
                        <td>{d.tj_career_sleeper.manager}</td>
                        <td class="num">{d.tj_career_sleeper.seasons_played}</td>
                        <td class="num">{d.tj_career_sleeper.wins}-{d.tj_career_sleeper.losses}{d.tj_career_sleeper.ties ? `-${d.tj_career_sleeper.ties}` : ''}</td>
                        <td class="num">{(d.tj_career_sleeper.win_pct * 100).toFixed(1)}%</td>
                        <td class="num">{d.tj_career_sleeper.points_for.toFixed(0)}</td>
                        <td class="num">{d.tj_career_sleeper.championships}</td>
                        <td class="num">{d.tj_career_sleeper.runner_ups}</td>
                    </tr>
                </tbody>
            </table>
        {:else}
            <p class="sub">No matching Sleeper account found by display-name pattern.</p>
        {/if}

        <h2>The runner-up curse</h2>
        <ul>
            <li><strong>2014</strong>: T.J.R's Team — lost to Colt's The Patriot Act 90.12 – 107.68</li>
            <li><strong>2019</strong>: Kareem Punt — lost to LordPmp's Quadfather 119.12 – 147.76</li>
            <li><strong>2020</strong>: Kareem Punt — lost to Joey's Waller Walkers 119.70 – 123.46 <em>(closest of the three)</em></li>
        </ul>
    {:catch e}
        <p style="color:#b00">Couldn't load: {e.message}</p>
    {/await}
</div>
