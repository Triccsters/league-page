<script>
    import { onMount } from 'svelte';
    import TimelineChart from '$lib/Timeline/TimelineChart.svelte';
    import { leagueID } from '$lib/utils/leagueInfo';
    import { loadPlayers } from '$lib/utils/helper';
    import { nameOf, slugFor, site } from '$lib/utils/flpHistory';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';
    import { myTeam } from '$lib/utils/myTeam';

    const SLOTS = ['Wed', 'Thu', 'Sun early', 'Sun late', 'SNF', 'MNF'];
    const CANON = { Austin7Rock: 'RockMNwild', Tongueohvaeloa: 'TuanonStan' };
    const S = (p) => fetch(`https://api.sleeper.app/v1${p}`).then(r => r.json());

    let week = null, maxWeek = 1, season = null;
    let loading = true, error = '', games = [], updated = '';
    let base = null;   // users, rosters, players, fetched once

    // Name the kickoff window in US Central time.
    const slotFor = (iso) => {
        const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
            timeZone: 'America/Chicago', weekday: 'short', hour: 'numeric', hour12: false,
        }).formatToParts(new Date(iso)).map(p => [p.type, p.value]));
        const h = Number(parts.hour) % 24, d = parts.weekday;
        if (d === 'Wed') return 'Wed';
        if (d === 'Thu' || d === 'Fri' || d === 'Sat') return 'Thu';
        if (d === 'Sun') return h < 14 ? 'Sun early' : h < 18 ? 'Sun late' : 'SNF';
        return 'MNF';
    };

    const load = async () => {
        loading = true; error = '';
        try {
            if (!base) {
                const [users, rosters, league, pl] = await Promise.all([
                    S(`/league/${leagueID}/users`), S(`/league/${leagueID}/rosters`),
                    S(`/league/${leagueID}`), loadPlayers(),
                ]);
                const uname = Object.fromEntries(users.map(u => [u.user_id, CANON[u.display_name] || u.display_name]));
                base = {
                    handle: Object.fromEntries(rosters.map(r => [r.roster_id, uname[r.owner_id] || `Roster ${r.roster_id}`])),
                    players: pl.players,
                    season: league.season,
                };
                season = base.season;
            }
            const [matchups, board] = await Promise.all([
                S(`/league/${leagueID}/matchups/${week}`),
                fetch(`https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=${week}&seasontype=2&dates=${season}`).then(r => r.json()),
            ]);
            const slotOf = {}, status = {};
            for (const ev of board.events || []) {
                const s = slotFor(ev.date);
                for (const c of ev.competitions[0].competitors) {
                    const ab = c.team.abbreviation === 'WSH' ? 'WAS' : c.team.abbreviation;
                    slotOf[ab] = s;
                }
                status[s] = status[s] || [];
                status[s].push(ev.status.type.state);   // pre / in / post
            }
            // A window counts once any of its games has kicked off.
            const started = SLOTS.map(s => (status[s] || []).some(x => x !== 'pre'));
            const lastStarted = started.lastIndexOf(true);

            const byId = {};
            for (const m of matchups) {
                if (m.matchup_id == null) continue;
                (byId[m.matchup_id] ||= []).push(m);
            }
            games = Object.values(byId).filter(p => p.length === 2).map(pair => {
                const sides = pair.map(m => {
                    const run = Object.fromEntries(SLOTS.map(s => [s, 0]));
                    (m.starters || []).forEach((pid, i) => {
                        const team = base.players[pid]?.t || pid;
                        const s = slotOf[team];
                        if (s) run[s] += m.starters_points?.[i] || 0;
                    });
                    let acc = 0;
                    const values = SLOTS.map((s, i) => {
                        acc += run[s];
                        return i <= Math.max(lastStarted, 0) ? Math.round(acc * 100) / 100 : null;
                    }).filter(v => v !== null);
                    return { manager: base.handle[m.roster_id], points: Math.round((m.points || 0) * 100) / 100, values };
                });
                sides.sort((a, b) => b.points - a.points);
                return sides;
            }).sort((a, b) => (a[0].points - a[1].points) - (b[0].points - b[1].points));
            updated = new Date().toLocaleTimeString();
        } catch (e) {
            error = 'Could not load this week from Sleeper or ESPN. Try again in a minute.';
            console.error(e);
        }
        loading = false;
    };

    onMount(async () => {
        const st = await S('/state/nfl');
        maxWeek = Math.min(18, Math.max(1, st.display_week || st.week || 1));
        week = maxWeek;
        await load();
        // Before the week's first kickoff every game is 0-0; open on the last week with scores
        if (week > 1 && games.length && games.every(([a, b]) => !a.points && !b.points)) {
            week -= 1;
            await load();
        }
    });
</script>

<svelte:head><title>Matchup Timeline | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>Matchup Timeline</h1>
    <p class="sub">How each game built up through the week: Thursday, the Sunday windows, and the night games. Blue is the team ahead. Your game shows first.</p>

    <div class="controls">
        <label>Week
            <select bind:value={week} on:change={load} disabled={loading}>
                {#each Array.from({ length: maxWeek }, (_, i) => i + 1) as w}<option value={w}>{w}</option>{/each}
            </select>
        </label>
        <button on:click={load} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
        {#if updated}<span class="stamp">Updated {updated}</span>{/if}
    </div>

    {#if error}<p class="err">{error}</p>{/if}

    {#each [...games].sort((p, q) => q.some(s => s.manager === $myTeam) - p.some(s => s.manager === $myTeam)) as [a, b]}
        <section class="game" class:mine={a.manager === $myTeam || b.manager === $myTeam}>
            <h3><a href="/rivalries/{slugFor(a.manager, b.manager)}">{nameOf(a.manager)} {a.points} – {b.points} {nameOf(b.manager)}</a>
                <YourTeamBadge handle={a.manager} size="small" /><YourTeamBadge handle={b.manager} size="small" /></h3>
            <TimelineChart slots={SLOTS.slice(0, Math.max(a.values.length, 1))}
                a={{ label: nameOf(a.manager), values: a.values }}
                b={{ label: nameOf(b.manager), values: b.values }} />
        </section>
    {/each}

    <p class="stamp">Finished weeks have a full write-up in <a href="/recaps">Weekly Recaps</a>.</p>
</div>

<style>
    .holder { max-width: 820px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub { text-align: center; opacity: 0.75; }
    .controls { display: flex; gap: 1em; justify-content: center; align-items: center; margin: 1em 0; flex-wrap: wrap; }
    select, button { padding: 0.35em 0.7em; font-size: 1em; margin-left: 0.4em; }
    .game { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.8em 1em; margin: 1em 0; }
    h3 { margin: 0; font-size: 1.05em; }
    .game.mine { border-color: #27ae60; box-shadow: inset 4px 0 0 #27ae60; }
    h3 a { color: inherit; }
    .stamp { opacity: 0.65; font-size: 0.85em; text-align: center; }
    .stamp a { color: #3498db; }
    .err { color: #e74c3c; text-align: center; }
</style>
