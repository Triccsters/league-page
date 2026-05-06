<script>
    import { historicalRecords } from '$lib/utils/historicalRecords';

    const groups = [
        { title: '🏈 Head-to-Head', key: 'head_to_head' },
        { title: '📐 Margin of Victory', key: 'margin_of_victory' },
        { title: '💯 Team Points', key: 'team_points' },
        { title: '⚔️ Offensive Points', key: 'offensive_points' },
        { title: '🛡️ Defensive Points', key: 'defensive_points' },
        { title: '🦵 Kicking Points', key: 'kicking_points' },
        { title: '🏆 Touchdowns', key: 'touchdowns' },
        { title: '📏 Yardage', key: 'yardage' },
        { title: '📅 Strength of Schedule', key: 'strength_of_schedule' },
    ];
</script>

<style>
    .holder {
        max-width: 1100px;
        margin: 0 auto;
        padding: 1.5em 1em;
    }
    h1 { text-align: center; }
    .sub { color: var(--g777, #777); text-align: center; font-size: 0.95em; margin-bottom: 2em; }
    h2 {
        margin-top: 2em;
        margin-bottom: 0.5em;
        font-size: 1.2em;
        border-bottom: 2px solid var(--ddd, #ddd);
        padding-bottom: 0.3em;
    }
    .record-row {
        display: grid;
        grid-template-columns: 1.2fr 1.4fr 0.5fr 0.7fr;
        gap: 1em;
        padding: 0.5em 0.6em;
        border-bottom: 1px solid var(--ddd, #ddd);
        font-size: 0.95em;
        align-items: center;
    }
    .stat-name { color: var(--g555, #888); }
    .holder-name { font-weight: 600; }
    .value { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
    .meta { text-align: right; color: var(--g777, #888); font-size: 0.88em; }
</style>

<div class="holder">
    <h1>📜 Record Book</h1>
    <p class="sub">All-time records across 11 captured seasons (2010, 2012–2020 Yahoo + Sleeper era). Sourced from Yahoo's Record Book + Sleeper API.</p>

    {#each groups as g}
        {#if historicalRecords[g.key]?.length}
            <h2>{g.title}</h2>
            {#each historicalRecords[g.key] as r}
                <div class="record-row">
                    <div class="stat-name">{r.stat}</div>
                    <div class="holder-name">{r.holder}</div>
                    <div class="value">{r.value}</div>
                    <div class="meta">{r.season}{r.week ? ` W${r.week}` : ''}</div>
                </div>
            {/each}
        {/if}
    {/each}
</div>
