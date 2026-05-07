<script>
    import { historicalRecords } from '$lib/utils/historicalRecords';
    export let data;
    const { allTimeData } = data;

    const yahooGroups = [
        { title: 'Head-to-Head', key: 'head_to_head' },
        { title: 'Margin of Victory', key: 'margin_of_victory' },
        { title: 'Team Points', key: 'team_points' },
        { title: 'Offensive Points', key: 'offensive_points' },
        { title: 'Defensive Points', key: 'defensive_points' },
        { title: 'Kicking Points', key: 'kicking_points' },
        { title: 'Touchdowns', key: 'touchdowns' },
        { title: 'Yardage', key: 'yardage' },
        { title: 'Strength of Schedule', key: 'strength_of_schedule' },
    ];
</script>

<style>
    .holder { max-width: 1100px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; }
    .sub { color: var(--g777, #777); text-align: center; font-size: 0.95em; margin-bottom: 2em; }
    .era { margin-top: 2.5em; padding-top: 1em; border-top: 3px solid var(--ddd, #ddd); }
    h2 { margin-top: 1.5em; margin-bottom: 0.5em; font-size: 1.2em; border-bottom: 1px solid var(--ddd, #ddd); padding-bottom: 0.3em; }
    .era-banner { font-size: 1.4em; font-weight: 600; margin-bottom: 0.3em; padding: 0.4em 0.8em; border-radius: 4px; display: inline-block; }
    .era-banner.yahoo { background: rgba(155, 89, 182, 0.15); color: #b07cd2; }
    .era-banner.sleeper { background: rgba(241, 156, 28, 0.15); color: #d6a04a; }
    .record-row {
        display: grid;
        grid-template-columns: 1.4fr 1.2fr 0.8fr 0.5fr 0.7fr;
        gap: 0.8em;
        padding: 0.5em 0.6em;
        border-bottom: 1px solid var(--ddd, #ddd);
        font-size: 0.92em;
        align-items: center;
    }
    .stat-name { color: var(--g555, #888); }
    .holder-name { font-weight: 600; }
    .opp { color: var(--g777, #888); font-size: 0.85em; font-style: italic; }
    .value { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
    .meta { text-align: right; color: var(--g777, #888); font-size: 0.85em; }
    .top-list { font-size: 0.92em; }
</style>

<div class="holder">
    <h1>📜 Record Book</h1>
    <p class="sub">All-time records across both eras of the FL Players league.</p>

    <div class="era">
        <span class="era-banner sleeper">🟠 Sleeper era (2021–present)</span>
        <p class="sub" style="text-align:left">Computed live from Sleeper API. Top 5 per category.</p>

        {#await allTimeData}
            <p class="sub">Loading...</p>
        {:then d}
            {#if d.sleeper_records}
                <h2>💯 Highest single-week scores</h2>
                {#each d.sleeper_records.highest_single_week as r}
                    <div class="record-row">
                        <div class="stat-name">#{d.sleeper_records.highest_single_week.indexOf(r) + 1}</div>
                        <div class="holder-name">{r.holder} <span class="opp">vs {r.opponent}</span></div>
                        <div></div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season} W{r.week}</div>
                    </div>
                {/each}

                <h2>🐢 Lowest single-week scores</h2>
                {#each d.sleeper_records.lowest_single_week as r}
                    <div class="record-row">
                        <div class="stat-name">#{d.sleeper_records.lowest_single_week.indexOf(r) + 1}</div>
                        <div class="holder-name">{r.holder} <span class="opp">vs {r.opponent}</span></div>
                        <div></div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season} W{r.week}</div>
                    </div>
                {/each}

                <h2>💥 Biggest blowouts</h2>
                {#each d.sleeper_records.biggest_blowouts as r}
                    <div class="record-row">
                        <div class="stat-name">#{d.sleeper_records.biggest_blowouts.indexOf(r) + 1}</div>
                        <div class="holder-name">{r.holder}</div>
                        <div class="opp">def. {r.opponent} by</div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season} W{r.week}</div>
                    </div>
                {/each}

                <h2>🪒 Closest games</h2>
                {#each d.sleeper_records.closest_games as r}
                    <div class="record-row">
                        <div class="stat-name">#{d.sleeper_records.closest_games.indexOf(r) + 1}</div>
                        <div class="holder-name">{r.holder}</div>
                        <div class="opp">edged {r.opponent} by</div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season} W{r.week}</div>
                    </div>
                {/each}

                <h2>📈 Highest single-season totals</h2>
                {#each d.sleeper_records.highest_season as r}
                    <div class="record-row">
                        <div class="stat-name">#{d.sleeper_records.highest_season.indexOf(r) + 1}</div>
                        <div class="holder-name">{r.holder}</div>
                        <div></div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season}</div>
                    </div>
                {/each}

                <h2>📉 Lowest single-season totals</h2>
                {#each d.sleeper_records.lowest_season as r}
                    <div class="record-row">
                        <div class="stat-name">#{d.sleeper_records.lowest_season.indexOf(r) + 1}</div>
                        <div class="holder-name">{r.holder}</div>
                        <div></div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season}</div>
                    </div>
                {/each}
            {/if}
        {:catch e}
            <p style="color:#b00">Couldn't load: {e.message}</p>
        {/await}
    </div>

    <div class="era">
        <span class="era-banner yahoo">🟣 Yahoo era (2010–2020)</span>
        <p class="sub" style="text-align:left">Transcribed from Yahoo's Record Book. Some records have an opponent context (vs &lt;team&gt;) since they were set in a specific matchup.</p>

        {#each yahooGroups as g}
            {#if historicalRecords[g.key]?.length}
                <h2>{g.title}</h2>
                {#each historicalRecords[g.key] as r}
                    <div class="record-row">
                        <div class="stat-name">{r.stat}</div>
                        <div class="holder-name">{r.holder}</div>
                        <div class="opp">{r.opponent ? `vs ${r.opponent}` : ''}</div>
                        <div class="value">{r.value}</div>
                        <div class="meta">{r.season}{r.week ? ` W${r.week}` : ''}</div>
                    </div>
                {/each}
            {/if}
        {/each}
    </div>
</div>
