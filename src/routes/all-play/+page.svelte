<script>
    export let data;
    const { allPlayData } = data;
</script>

<style>
    .holder {
        max-width: 900px;
        margin: 0 auto;
        padding: 1.5em 1em;
        text-align: center;
    }
    h1 {
        margin-bottom: 0.2em;
    }
    .sub {
        color: var(--g777, #777);
        margin-bottom: 1.5em;
        font-size: 0.95em;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1em;
    }
    th, td {
        padding: 0.6em 0.5em;
        border-bottom: 1px solid var(--ddd, #ddd);
        text-align: left;
        font-size: 0.95em;
    }
    th {
        background: var(--fff, #fafafa);
        font-weight: 600;
    }
    .num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .rank {
        text-align: center;
        font-weight: 600;
        width: 3em;
    }
    .pct {
        font-weight: 600;
    }
    .top1 td { background: rgba(255, 215, 0, 0.12); }
    .top2 td { background: rgba(192, 192, 192, 0.10); }
    .top3 td { background: rgba(205, 127, 50, 0.10); }
    .explainer {
        max-width: 700px;
        margin: 0 auto 1.5em;
        text-align: left;
        font-size: 0.95em;
        color: var(--g555, #555);
        line-height: 1.5;
    }
    .explainer strong {
        color: var(--g333, #333);
    }
</style>

<div class="holder">
    <h1>All-Play Standings</h1>

    {#await allPlayData}
        <p class="sub">Loading season data from Sleeper...</p>
    {:then d}
        <p class="sub">{d.leagueName} · {d.season} · weeks {d.weeksIncluded[0]}–{d.weeksIncluded[d.weeksIncluded.length - 1]}</p>

        <div class="explainer">
            <strong>What is "all-play"?</strong> It's what each team's record would be <em>if they played every other team every week</em>. Strips out luck-of-the-schedule and shows who's actually the best (and worst) team in the league based purely on weekly scoring.
        </div>

        <table>
            <thead>
                <tr>
                    <th class="rank">#</th>
                    <th>Team</th>
                    <th>Manager</th>
                    <th class="num">All-Play Record</th>
                    <th class="num">Win %</th>
                    <th class="num">Points For</th>
                </tr>
            </thead>
            <tbody>
                {#each d.rows as row}
                    <tr class:top1={row.rank === 1} class:top2={row.rank === 2} class:top3={row.rank === 3}>
                        <td class="rank">{row.rank}</td>
                        <td>{row.team}</td>
                        <td>{row.manager}</td>
                        <td class="num">{row.all_play_w}-{row.all_play_l}{row.all_play_t ? `-${row.all_play_t}` : ''}</td>
                        <td class="num pct">{(row.all_play_pct * 100).toFixed(1)}%</td>
                        <td class="num">{row.points_for.toFixed(2)}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {:catch e}
        <p class="sub" style="color: #b00;">Couldn't load: {e.message}</p>
    {/await}
</div>
