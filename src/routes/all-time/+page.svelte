<script>
    export let data;
    const { allTimeData } = data;
</script>

<style>
    .holder {
        max-width: 1100px;
        margin: 0 auto;
        padding: 1.5em 1em;
        text-align: center;
    }
    h1 { margin-bottom: 0.2em; }
    h2 {
        margin-top: 2em;
        margin-bottom: 0.5em;
        text-align: left;
        font-size: 1.3em;
        border-bottom: 2px solid var(--ddd, #ddd);
        padding-bottom: 0.3em;
    }
    .sub {
        color: var(--g777, #777);
        margin-bottom: 1.5em;
        font-size: 0.95em;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.5em;
    }
    th, td {
        padding: 0.5em 0.5em;
        border-bottom: 1px solid var(--ddd, #ddd);
        text-align: left;
        font-size: 0.92em;
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
    .top1 td { background: rgba(255, 215, 0, 0.12); }
    .ringspot {
        font-size: 1.1em;
    }
    .records-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5em;
        margin-top: 1em;
        text-align: left;
    }
    .record-card {
        background: var(--fff, #fafafa);
        border: 1px solid var(--ddd, #ddd);
        border-radius: 6px;
        padding: 1em;
    }
    .record-card h3 {
        margin: 0 0 0.5em;
        font-size: 1em;
    }
    .record-card ol {
        margin: 0;
        padding-left: 1.5em;
        font-size: 0.9em;
    }
    .record-card li {
        margin-bottom: 0.4em;
    }
    .explainer {
        max-width: 800px;
        margin: 0 auto 1.5em;
        text-align: left;
        font-size: 0.95em;
        color: var(--g555, #555);
        line-height: 1.5;
    }
</style>

<div class="holder">
    <h1>All-Time Stats</h1>

    {#await allTimeData}
        <p class="sub">Walking back through every season... (this can take 5–15 sec for older leagues)</p>
    {:then d}
        {#if d.error}
            <p class="sub" style="color:#b00">{d.error}</p>
        {:else}
            <p class="sub">{d.league_name_current} · {d.seasons_count} season{d.seasons_count === 1 ? '' : 's'} ({d.season_range})</p>

            <div class="explainer">
                Aggregates every matchup across every season this league has ever played. Champions are pulled from each season's playoff bracket. Manager stats follow the user across seasons (so if your team name changed, your record didn't reset).
            </div>

            <h2>🏆 Champions by season</h2>
            <table>
                <thead>
                    <tr>
                        <th>Season</th>
                        <th>Platform</th>
                        <th>Champion</th>
                        <th>Team</th>
                        <th>Runner-up</th>
                    </tr>
                </thead>
                <tbody>
                    {#each d.champions as c}
                        <tr>
                            <td><strong>{c.season}</strong></td>
                            <td>{c.platform === 'yahoo' ? '🟣 Yahoo' : c.platform === 'sleeper' ? '🟠 Sleeper' : c.platform}</td>
                            <td class="ringspot">🥇 {c.champion}</td>
                            <td>{c.champion_team}</td>
                            <td>{c.runner_up}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>

            <h2>📊 All-time manager standings</h2>
            <table>
                <thead>
                    <tr>
                        <th class="rank">#</th>
                        <th>Manager</th>
                        <th class="num">Seasons</th>
                        <th class="num">W-L-T</th>
                        <th class="num">Win %</th>
                        <th class="num">Points For</th>
                        <th class="num">🏆</th>
                        <th class="num">2nd</th>
                        <th>Best single week</th>
                    </tr>
                </thead>
                <tbody>
                    {#each d.manager_rows as m}
                        <tr class:top1={m.rank === 1}>
                            <td class="rank">{m.rank}</td>
                            <td>{m.manager}</td>
                            <td class="num">{m.seasons_played}</td>
                            <td class="num">{m.wins}-{m.losses}{m.ties ? `-${m.ties}` : ''}</td>
                            <td class="num">{(m.win_pct * 100).toFixed(1)}%</td>
                            <td class="num">{m.points_for.toFixed(0)}</td>
                            <td class="num">{m.championships}</td>
                            <td class="num">{m.runner_ups}</td>
                            <td>{m.biggest_score}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>

            <h2>📜 League records</h2>
            <div class="records-grid">
                <div class="record-card">
                    <h3>💥 Biggest blowouts ever</h3>
                    <ol>
                        {#each d.biggest_blowouts as b}
                            <li><strong>{b.winner}</strong> beat {b.loser} by <strong>{b.margin}</strong> ({b.winner_pts}–{b.loser_pts}, {b.season} W{b.week})</li>
                        {/each}
                    </ol>
                </div>
                <div class="record-card">
                    <h3>🪒 Closest games ever</h3>
                    <ol>
                        {#each d.closest_games as c}
                            <li><strong>{c.winner}</strong> edged {c.loser} by <strong>{c.margin}</strong> ({c.winner_pts}–{c.loser_pts}, {c.season} W{c.week})</li>
                        {/each}
                    </ol>
                </div>
                <div class="record-card">
                    <h3>🔥 Highest single-week scores</h3>
                    <ol>
                        {#each d.highest_scores as s}
                            <li><strong>{s.team}</strong> — {s.pts} ({s.season} W{s.week})</li>
                        {/each}
                    </ol>
                </div>
            </div>
        {/if}
    {:catch e}
        <p class="sub" style="color: #b00;">Couldn't load: {e.message}</p>
    {/await}
</div>
