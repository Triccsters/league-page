<script>
    import PlayoffRace from '$lib/Charts/PlayoffRace.svelte';
    import { onMount } from 'svelte';
    import odds from '$lib/data/odds.json';
    import { nameOf, teamName, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';

    let ready = false;
    onMount(() => { ready = true; });
    const mine = (h) => ready && h === $myTeam;

    const N = odds.playoff_teams || 6;
    const BYES = odds.bye_teams ?? (N >= 6 ? 2 : 0);
    const byRecord = (a, b) => b.w - a.w || b.pf - a.pf;
    const divisions = odds.divisions || {};
    const hasDiv = Object.keys(divisions).length > 0;

    // seed the way the league does: division winners first where there are
    // divisions, then record, then points
    function seedOrder(teams) {
        const all = [...teams].sort(byRecord);
        if (!hasDiv) return all;
        const winners = [];
        for (const d of [...new Set(Object.values(divisions))]) {
            const top = all.find((t) => divisions[t.h] === d);
            if (top) winners.push(top);
        }
        winners.sort(byRecord);
        return [...winners, ...all.filter((t) => !winners.includes(t))];
    }
    const order = seedOrder(odds.teams);
    const seedOf = Object.fromEntries(order.map((t, i) => [t.h, i + 1]));
    const team = Object.fromEntries(odds.teams.map((t) => [t.h, t]));
    const field = order.slice(0, N);
    const line = field[field.length - 1];
    const firstOut = order[N];

    // first round: seeds without a bye, best against worst
    const playing = field.slice(BYES);
    const firstRound = [];
    for (let i = 0; i < Math.floor(playing.length / 2); i++) {
        firstRound.push([playing[i], playing[playing.length - 1 - i]]);
    }

    // how far a team is from the last playoff spot
    function gap(t) {
        const s = seedOf[t.h];
        if (s <= N) {
            if (!firstOut) return '';
            const g = t.w - firstOut.w;
            return g > 0 ? `${g} up` : `${(t.pf - firstOut.pf).toFixed(1)} pts up`;
        }
        const g = line.w - t.w;
        return g > 0 ? `${g} back` : `${(line.pf - t.pf).toFixed(1)} pts back`;
    }
    function status(t) {
        if (t.playoff >= 99.5) return ['lock', 'Near lock'];
        if (t.playoff >= 75) return ['good', 'Likely in'];
        if (t.playoff >= 25) return ['bubble', 'On the bubble'];
        if (t.playoff > 0.5) return ['long', 'Long shot'];
        return ['out', 'Needs a miracle'];
    }
    const pct = (v) => (v >= 99.95 ? '>99.9' : v > 0 && v < 0.1 ? '<0.1' : v.toFixed(1)) + '%';
    const rec = (h) => (team[h] ? `${team[h].w}-${team[h].l}` : '');

    // games still to play, flagged when both teams are still fighting for a spot
    const live = (h) => team[h] && team[h].playoff > 10 && team[h].playoff < 90;
    const byeRace = (h) => team[h] && team[h].bye > 5 && team[h].bye < 95;
    const weeks = (odds.remaining_weeks || []).map((w) => ({
        w,
        games: ((odds.schedule || {})[w] || []).map(([a, b]) => ({
            a, b,
            tag: live(a) && live(b) ? 'Playoff spot' : byeRace(a) && byeRace(b) ? 'Bye' : '',
        })).sort((x, y) => (y.tag ? 1 : 0) - (x.tag ? 1 : 0)),
    }));
</script>

<svelte:head><title>Playoff Picture</title></svelte:head>

<div class="holder">
    <h1>Playoff Picture</h1>
    <p class="sub">After week {odds.through_week} of {odds.season}. Top {N} make the playoffs{BYES ? `, top ${BYES} get a bye` : ''}{hasDiv ? ', division winners seeded first' : ''}. Playoffs start in week {odds.playoff_start}.</p>

    <PlayoffRace />

    <h2>If the season ended today</h2>
    <div class="today">
        <div class="seeds">
            {#each field as t, i}
                <div class="seed" class:mine={mine(t.h)}>
                    <span class="n">{i + 1}</span>
                    <span class="who"><b>{nameOf(t.h)}</b><YourTeamBadge handle={t.h} size="small" />
                        {#if teamName(site.season, t.h) && teamName(site.season, t.h) !== nameOf(t.h)}<small>{teamName(site.season, t.h)}</small>{/if}</span>
                    <span class="r">{t.w}-{t.l}</span>
                    {#if i < BYES}<span class="tag bye">Bye</span>{/if}
                </div>
            {/each}
            {#if firstOut}
                <div class="cut">playoff line</div>
                <div class="seed outside" class:mine={mine(firstOut.h)}>
                    <span class="n">{N + 1}</span>
                    <span class="who"><b>{nameOf(firstOut.h)}</b><YourTeamBadge handle={firstOut.h} size="small" /><small>first team out, {gap(firstOut)}</small></span>
                    <span class="r">{firstOut.w}-{firstOut.l}</span>
                </div>
            {/if}
        </div>
        <div class="round">
            <h3>First round</h3>
            {#each firstRound as [hi, lo]}
                <div class="game"><span><i>{seedOf[hi.h]}</i> {nameOf(hi.h)}</span><em>v</em><span><i>{seedOf[lo.h]}</i> {nameOf(lo.h)}</span></div>
            {/each}
            {#if BYES}
                <p class="note">{field.slice(0, BYES).map((t) => nameOf(t.h)).join(' and ')} would sit out the first round.</p>
            {/if}
        </div>
    </div>

    <h2>Where every team stands</h2>
    <div class="scroll">
        <table>
            <thead><tr><th class="num">Seed</th><th>Team</th><th>W-L</th><th class="num">Points</th><th>From the line</th><th class="bar">Playoffs</th>{#if BYES}<th class="num">Bye</th>{/if}<th>Outlook</th><th>Still to play</th></tr></thead>
            <tbody>
                {#each order as t, i}
                    {@const st = status(t)}
                    <tr class:mine={mine(t.h)} class:below={i === N}>
                        <td class="num">{i + 1}</td>
                        <td><b>{nameOf(t.h)}</b><YourTeamBadge handle={t.h} size="small" /></td>
                        <td>{t.w}-{t.l}</td>
                        <td class="num">{t.pf.toFixed(1)}</td>
                        <td>{gap(t)}</td>
                        <td class="bar"><div class="meter"><span style="width:{t.playoff}%"></span><em>{pct(t.playoff)}</em></div></td>
                        {#if BYES}<td class="num">{pct(t.bye)}</td>{/if}
                        <td><span class="pill {st[0]}">{st[1]}</span></td>
                        <td class="opps">{#each t.rest_opponents || [] as o, j}{j ? ', ' : ''}{nameOf(o)} <small>({rec(o)})</small>{/each}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>
    <p class="note">"From the line" is the gap to the last playoff spot: games first, then points when the records match. Outlook comes from the <a href="/odds">playoff odds</a>, which are a simulation and not a guarantee.</p>

    {#if weeks.length}
        <h2>The games left</h2>
        <p class="note">Marked games have a playoff spot or a bye riding on them for both teams.</p>
        <div class="weeks">
            {#each weeks as wk}
                <div class="week">
                    <h3>Week {wk.w}</h3>
                    {#each wk.games as g}
                        <div class="g" class:hot={g.tag === 'Playoff spot' || g.tag === 'Bye'} class:minegame={mine(g.a) || mine(g.b)}>
                            <span>{nameOf(g.a)} <small>{rec(g.a)}</small></span><em>v</em><span>{nameOf(g.b)} <small>{rec(g.b)}</small></span>
                            {#if g.tag}<b class="why">{g.tag}</b>{/if}
                        </div>
                    {/each}
                </div>
            {/each}
        </div>
    {:else}
        <p class="note">The regular season is over. The bracket is on the <a href="/matchups">Matchups</a> page.</p>
    {/if}
</div>

<style>
    .holder { max-width: 1040px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.6em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { margin: 0 0 0.4em; font-size: 1em; }
    .sub, .note { text-align: center; opacity: 0.75; font-size: 0.92em; }
    .note a { color: #3498db; }
    .today { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 1.2em; margin-top: 1em; }
    .seed { display: flex; align-items: center; gap: 0.6em; padding: 0.45em 0.6em; border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; margin-bottom: 0.35em; }
    .seed.mine, tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .seed.outside { opacity: 0.8; border-style: dashed; }
    .seed .n { width: 1.7em; height: 1.7em; line-height: 1.7em; text-align: center; border-radius: 50%; background: #3498db; color: #fff; font-weight: 700; flex: none; }
    .seed.outside .n { background: rgba(127,127,127,0.5); }
    .seed .who { flex: 1; min-width: 0; }
    .seed small, td small { display: block; opacity: 0.65; font-style: italic; }
    .seed .r { font-variant-numeric: tabular-nums; font-weight: 600; }
    .tag.bye { background: #f1c40f; color: #111; border-radius: 10px; padding: 0.05em 0.55em; font-size: 0.78em; font-weight: 700; }
    .cut { text-align: center; font-size: 0.75em; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.7; border-top: 2px dashed #e74c3c; margin: 0.6em 0 0.5em; padding-top: 0.2em; color: #e74c3c; }
    .round { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.8em 1em; align-self: start; }
    .game { display: flex; align-items: center; justify-content: space-between; gap: 0.5em; padding: 0.5em 0; border-bottom: 1px solid rgba(127,127,127,0.2); }
    .game i { font-style: normal; display: inline-block; min-width: 1.4em; text-align: center; border-radius: 4px; background: rgba(127,127,127,0.25); font-size: 0.82em; font-weight: 700; margin-right: 0.3em; }
    .game em, .g em { font-style: normal; opacity: 0.55; font-size: 0.85em; }
    .scroll { overflow-x: auto; margin-top: 1em; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.22); text-align: left; font-size: 0.92em; white-space: nowrap; }
    tr.below td { border-top: 2px dashed #e74c3c; }
    td.opps { white-space: normal; min-width: 430px; font-size: 0.86em; }
    td.opps small { display: inline; font-style: normal; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .bar { min-width: 140px; }
    .meter { position: relative; height: 1.4em; background: rgba(127,127,127,0.18); border-radius: 4px; overflow: hidden; }
    .meter span { position: absolute; left: 0; top: 0; bottom: 0; background: #3498db; }
    .meter em { position: relative; font-style: normal; font-weight: 700; padding-left: 0.4em; line-height: 1.4em; color: #fff; text-shadow: 0 0 3px #000; }
    .pill { border-radius: 10px; padding: 0.1em 0.6em; font-size: 0.82em; font-weight: 700; color: #fff; }
    .pill.lock { background: #1e8449; }
    .pill.good { background: #2980b9; }
    .pill.bubble { background: #d68910; }
    .pill.long { background: #8e44ad; }
    .pill.out { background: #7f8c8d; }
    .weeks { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 1em; margin-top: 0.8em; }
    .week { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.7em 0.9em; }
    .g { display: flex; align-items: center; gap: 0.45em; flex-wrap: wrap; padding: 0.35em 0.3em; border-bottom: 1px solid rgba(127,127,127,0.18); font-size: 0.9em; }
    .g small { opacity: 0.6; }
    .g.hot { border-left: 3px solid #e74c3c; padding-left: 0.5em; }
    .g.minegame { background: rgba(39, 174, 96, 0.12); }
    .why { margin-left: auto; font-size: 0.74em; text-transform: uppercase; letter-spacing: 0.05em; color: #e74c3c; }
    @media (max-width: 720px) { .today { grid-template-columns: 1fr; } }
</style>
