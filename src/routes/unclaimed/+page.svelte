<script>
    import { leagueName } from '$lib/utils/helper';

    export let data;
    $: ({teams, slug, team, prev, next} = data);

    const ordinal = (n) => {
        const s = ["th", "st", "nd", "rd"], v = n % 100;
        return n + (s[(v - 20) % 10] || s[v] || s[0]);
    };

    // "2008, 2010" or "2012 to 2013" when they run together
    const spanOf = (seasons) => seasons.length > 1 && seasons[seasons.length - 1] - seasons[0] === seasons.length - 1
        ? `${seasons[0]} to ${seasons[seasons.length - 1]}`
        : seasons.join(', ');

    // An unidentified team is keyed by its team name, so a team listed in more than one
    // season is only "the same team" in the sense that both used that name. Yahoo hid the
    // manager in those seasons, and the scrape kept no owner id, so it could be one
    // manager or two, and the page says so rather than implying a career.
    const nameOnlyLink = (t) => t.seasons.length > 1;

    const badgeOf = (t) => t.titles.length
        ? `Won it all in ${t.titles.join(', ')}`
        : (t.finalsLost.length ? `Lost the final in ${t.finalsLost.join(', ')}` : null);
</script>

<style>
    .main {
        width: 97%;
        max-width: 800px;
        margin: 0 auto 5em;
        position: relative;
        z-index: 1;
    }

    h1 {
        text-align: center;
        font-size: 2.6em;
        margin: 2em 0 0.5em;
        line-height: 1.1em;
    }

    h3 {
        font-size: 1.3em;
        font-weight: 200;
        margin: 2em 0 0.5em;
        text-align: center;
    }

    .intro {
        text-align: center;
        color: var(--g555);
        line-height: 1.6em;
        margin: 0 auto 1em;
        max-width: 620px;
    }

    .ask {
        display: block;
        margin: 1.5em auto 2.5em;
        padding: 1em 1.5em;
        max-width: 620px;
        border: 1px dashed var(--ccc);
        border-radius: 1.5em;
        background-color: var(--fff);
        color: var(--g555);
        text-align: center;
        line-height: 1.5em;
    }

    .card {
        display: block;
        background-color: var(--fff);
        border: 1px solid var(--ccc);
        border-radius: 1.5em;
        box-shadow: 0 0 6px 0 var(--bbb);
        margin: 0.8em 0;
        padding: 1em 1.3em;
        color: inherit;
        text-decoration: none;
    }

    a.card:hover {
        box-shadow: 0 0 10px 0 var(--bbb);
    }

    .cardTop {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0.6em;
    }

    .teamName {
        font-weight: 700;
        font-size: 1.15em;
    }

    .years {
        color: var(--g555);
        font-style: italic;
        font-size: 0.9em;
    }

    .spacer {
        flex-grow: 1;
    }

    .record {
        font-weight: 700;
        color: var(--g555);
    }

    .badge {
        display: inline-block;
        font-size: 0.78em;
        font-weight: 700;
        padding: 0.25em 0.7em;
        border-radius: 1em;
        background-color: var(--blueTwo);
        border: 1px solid var(--blueOne);
        color: #fff;
    }

    .caveat {
        margin: 0 auto 1.5em;
        max-width: 620px;
        padding: 1em 1.3em;
        border: 1px solid var(--ccc);
        border-left: 5px solid var(--blueTwo);
        border-radius: 0.8em;
        background-color: var(--fff);
        color: var(--g555);
        line-height: 1.6em;
        font-size: 0.95em;
    }

    .cardWarn {
        margin-top: 0.4em;
        font-size: 0.85em;
        font-weight: 700;
        color: var(--g555);
    }

    .cardLines {
        margin-top: 0.5em;
        color: var(--g555);
        font-size: 0.9em;
        line-height: 1.6em;
    }

    .statRow {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.6em;
        margin: 1em 0 0.5em;
    }

    .stat {
        background-color: var(--fff);
        border: 1px solid var(--ccc);
        border-radius: 1em;
        padding: 0.7em 1.1em;
        text-align: center;
        min-width: 120px;
    }

    .statNum {
        font-size: 1.5em;
        font-weight: 700;
        line-height: 1.1em;
    }

    .statLabel {
        font-size: 0.78em;
        color: var(--g555);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.5em 0 0;
        font-size: 0.92em;
    }

    th, td {
        border-bottom: 1px solid var(--ccc);
        padding: 0.5em 0.4em;
        text-align: left;
    }

    th {
        font-size: 0.8em;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--g555);
        font-weight: 700;
    }

    td.num, th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }

    .win { color: var(--greenOne, #2b8a3e); font-weight: 700; }
    .loss { color: var(--redOne, #c92a2a); font-weight: 700; }
    .tie { color: var(--g555); font-weight: 700; }

    .roundTag {
        font-size: 0.78em;
        font-style: italic;
        color: var(--g555);
    }

    .seasonBlock {
        background-color: var(--fff);
        border: 1px solid var(--ccc);
        border-radius: 1.5em;
        box-shadow: 0 0 6px 0 var(--bbb);
        margin: 1em 0;
        padding: 1em 1.3em 0.5em;
    }

    .seasonHead {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0.6em;
        margin-bottom: 0.3em;
    }

    .nav {
        display: flex;
        justify-content: space-between;
        gap: 0.6em;
        margin: 2.5em 0 0;
        flex-wrap: wrap;
    }

    .nav a {
        color: var(--g555);
        font-weight: 700;
        text-decoration: none;
        padding: 0.6em 1em;
        border: 1px solid var(--ccc);
        border-radius: 1.5em;
        background-color: var(--fff);
    }

    .nav a:hover {
        box-shadow: 0 0 8px 0 var(--bbb);
    }

    @media (max-width: 520px) {
        h1 { font-size: 2em; }
        .stat { min-width: 90px; padding: 0.6em 0.8em; }
        .statNum { font-size: 1.2em; }
        table { font-size: 0.82em; }
    }
</style>

<svelte:head>
    <title>{team ? `${team.name} — unidentified teams` : `Unidentified teams`} | {leagueName}</title>
</svelte:head>

<div class="main">
{#if team}
    <!-- one team -->
    <h1>{team.name}</h1>
    <p class="intro">
        {spanOf(team.seasons)} · nobody has claimed this team.
        {#if badgeOf(team)}<br /><span class="badge">{badgeOf(team)}</span>{/if}
    </p>

    {#if nameOnlyLink(team)}
        <p class="caveat">
            <b>These {team.seasons.length} seasons may not be the same manager.</b>
            A team with no owner name is identified here by its team name, and nothing else
            links {team.seasons.join(' and ')} — Yahoo hid the manager in both, and the old
            scoreboards kept no owner id. The totals above add the seasons together, so read
            them as "teams called {team.name}", not as one person's career. Season by season,
            below, is the part that is certain.
        </p>
    {/if}

    <div class="statRow">
        <div class="stat"><div class="statNum">{team.record}</div><div class="statLabel">Regular season{#if nameOnlyLink(team)}, combined{/if}</div></div>
        <div class="stat"><div class="statNum">{team.gamesPlayed}</div><div class="statLabel">Games</div></div>
        <div class="stat"><div class="statNum">{team.pointsFor}</div><div class="statLabel">Points for</div></div>
        <div class="stat"><div class="statNum">{team.pointsAgainst}</div><div class="statLabel">Points against</div></div>
    </div>

    <p class="ask">
        Below is everything the league still has on this team: who it drafted, who scored
        for it, who it played and what it scored, week by week. If any of it rings a bell
        — a draft pick, a lineup, a beating — that is the whole point. Say so in the
        league chat and the team gets a name.
    </p>

    {#if team.teamNames.length > 1}
        <p class="intro">Went by {team.teamNames.map(n => `"${n}"`).join(' and ')}.</p>
    {/if}

    <h3>Best and worst week</h3>
    <div class="statRow">
        <div class="stat">
            <div class="statNum">{team.bestWeek.score}</div>
            <div class="statLabel">Week {team.bestWeek.week} vs {team.bestWeek.opponentName}</div>
        </div>
        <div class="stat">
            <div class="statNum">{team.worstWeek.score}</div>
            <div class="statLabel">Week {team.worstWeek.week} vs {team.worstWeek.opponentName}</div>
        </div>
    </div>

    {#if team.topPlayers.length}
        <h3>Who played for this team</h3>
        <p class="intro">Points scored while in this team's starting lineup.</p>
        <table>
            <thead>
                <tr>
                    <th>Player</th><th>Pos</th><th class="num">Points</th>
                    <th class="num">Starts</th><th>Season</th>
                </tr>
            </thead>
            <tbody>
                {#each team.topPlayers as p}
                    <tr>
                        <td>{p.name}</td>
                        <td>{p.pos}</td>
                        <td class="num">{p.points}</td>
                        <td class="num">{p.starts}</td>
                        <td>{p.seasons.join(', ')}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}

    {#if team.draft.length}
        <h3>What it drafted</h3>
        {#each team.draft as d}
            <div class="seasonBlock">
                <div class="seasonHead">
                    <span class="teamName">{d.season} draft</span>
                    <span class="spacer"></span>
                    <span class="record">{d.picks.length} picks</span>
                </div>
                <table>
                    <thead>
                        <tr><th>Rd</th><th>Pick</th><th>Player</th><th>Pos</th></tr>
                    </thead>
                    <tbody>
                        {#each d.picks as pk}
                            <tr>
                                <td>{pk.round}</td>
                                <td>{pk.pick}</td>
                                <td>{pk.player}</td>
                                <td>{pk.pos}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/each}
    {/if}

    <h3>Who it played</h3>
    <table>
        <thead>
            <tr><th>Opponent</th><th class="num">Won</th><th class="num">Lost</th></tr>
        </thead>
        <tbody>
            {#each team.playedMost as foe}
                <tr><td>{foe.name}</td><td class="num">{foe.w}</td><td class="num">{foe.l}</td></tr>
            {/each}
        </tbody>
    </table>

    {#each team.bySeason as season}
        <div class="seasonBlock">
            <div class="seasonHead">
                <span class="teamName">{season.season}</span>
                {#if season.teamName && season.teamName !== team.name}
                    <span class="years">as "{season.teamName}"</span>
                {/if}
                <span class="spacer" />
                <span class="record">{season.record}</span>
            </div>
            <div class="cardLines">
                {season.pointsFor} points for, {season.pointsAgainst} against.
                {#if season.wonTitle}
                    Won the championship.
                {:else if season.lostFinal}
                    Lost the championship game.
                {:else if season.madePlayoffs}
                    Made the playoffs: {season.playoffResults.join(', ')}.
                {:else if season.playoffResults.length}
                    Missed the playoffs ({season.playoffResults.join(', ')}).
                {:else}
                    Missed the playoffs.
                {/if}
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Wk</th><th>Opponent</th><th class="num">Score</th>
                        <th class="num">Against</th><th>Result</th>
                    </tr>
                </thead>
                <tbody>
                    {#each season.games as g}
                        <tr>
                            <td>
                                {g.week}
                                {#if g.playoff && g.label}<div class="roundTag">{g.label}</div>{/if}
                            </td>
                            <td>{g.opponentName}</td>
                            <td class="num">{g.score}</td>
                            <td class="num">{g.opponentScore}</td>
                            <td class={g.result === 'W' ? 'win' : (g.result === 'L' ? 'loss' : 'tie')}>{g.result}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/each}

    <div class="nav">
        {#if prev}<a href="/unclaimed?team={prev.slug}">&larr; {prev.name}</a>{:else}<span></span>{/if}
        <a href="/unclaimed">All unidentified teams</a>
        {#if next}<a href="/unclaimed?team={next.slug}">{next.name} &rarr;</a>{:else}<span></span>{/if}
    </div>

{:else}
    <!-- the index -->
    <h1>Teams we never identified</h1>
    <p class="intro">
        {leagueName} goes back to 2008, and the early Yahoo years came out of the old
        scoreboards without owner names attached. {teams.length} teams are still sitting
        there with a team name, a record and every game they played, and nobody attached
        to them.
    </p>
    <p class="ask">
        {#if slug}
            There is no team here called "{slug}". Pick one from the list.
        {:else}
            One of these might be yours, or someone you played against. Everything the
            league has on each of them is on its page — opponents, scores, week by week.
            If it jogs a memory, say so in the league chat.
        {/if}
    </p>

    {#each teams as t}
        <a class="card" href="/unclaimed?team={t.slug}">
            <div class="cardTop">
                <span class="teamName">{t.name}</span>
                <span class="years">{spanOf(t.seasons)}</span>
                <span class="spacer" />
                {#if badgeOf(t)}<span class="badge">{badgeOf(t)}</span>{/if}
                <span class="record">{t.record}</span>
            </div>
            {#if nameOnlyLink(t)}
                <div class="cardWarn">Two teams used this name. Possibly one manager, possibly two.</div>
            {/if}
            <div class="cardLines">
                {t.gamesPlayed} games · {t.pointsFor} points for, {t.pointsAgainst} against ·
                best week {t.bestWeek.score} in week {t.bestWeek.week} against {t.bestWeek.opponentName}
                {#if t.topPlayers.length}
                    <br /><b>Best players:</b> {t.topPlayers.slice(0, 4).map(p => p.name).join(', ')}
                {/if}
                {#if t.draft.length && t.draft[0].picks.length}
                    <br /><b>First pick, {t.draft[0].season}:</b> {t.draft[0].picks[0].player}
                {/if}
                {#if t.playedMost.length}
                    <br />Played most against {t.playedMost.slice(0, 3).map(f => f.name).join(', ')}
                {/if}
            </div>
        </a>
    {/each}

    <div class="nav">
        <a href="/managers">&larr; All managers</a>
        <a href="/records">League records</a>
    </div>
{/if}
</div>
