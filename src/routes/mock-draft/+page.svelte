<script>
    import { onMount, onDestroy } from 'svelte';
    import { myTeam, handleForUser } from '$lib/utils/myTeam';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import {
        createDraft, runCpuPick, draftPlayer, availablePlayers, currentTeam, currentPick,
        nextUserPick, autoDraftRest, playersOf,
    } from '$lib/mockdraft/draft';
    import { DEFAULT_CPU, describeProfile } from '$lib/mockdraft/cpu';
    import { gradeDraft } from '$lib/mockdraft/grade';
    import { survivalOdds } from '$lib/mockdraft/survival';
    import { liveBoard } from '$lib/mockdraft/liveAdp';
    import { openNeeds, repeatsAvailable, habitNow, simulateWindow, areaMix } from '$lib/mockdraft/insights';

    const POS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
    const PACE_MS = 140;

    let data = null, error = '', ready = false;
    let me = null;            // the handle you draft as
    let slot = 1;             // the draft slot you sit in
    let room = 'managers';    // 'managers' or 'adp'
    let engine = null, results = null, timer = null;
    let posFilter = 'ALL', search = '';
    let showHabits = false;

    onMount(async () => {
        ready = true;
        try {
            data = await fetch('/data/mock_draft.json').then((r) => r.json());
            me = $myTeam || null;
            slot = seatOfHandle(me) ?? 1;
        } catch (e) { error = 'Could not load the mock draft data.'; return; }
        // Swap in Sleeper's current ADP; the snapshot stands if that fails.
        try {
            const live = await liveBoard(data.players, data.league.scoring);
            if (live) { data = { ...data, players: live.players }; adpLive = live; }
        } catch { /* snapshot stands */ }
        adpChecking = false;
    });
    let adpLive = null, adpChecking = true;
    onDestroy(() => clearTimeout(timer));

    // Seats in slot order, as handles, from last year's draft order.
    $: seatHandles = data ? data.seats.map((s) => handleForUser(s.userId) || s.userId) : [];
    $: managersList = [...seatHandles].sort((a, b) => nameOf(a).localeCompare(nameOf(b)));
    const seatOfHandle = (h) => {
        const i = seatHandles.indexOf(h);
        return i >= 0 ? i + 1 : null;
    };
    const profileOf = (h) => {
        const seat = data?.seats.find((s) => (handleForUser(s.userId) || s.userId) === h);
        return seat ? data.profiles[seat.userId] || null : null;
    };
    let chosen = false; // set once you pick here; until then the YOUR TEAM bar decides
    function pickMe(h) { chosen = true; me = h || null; slot = seatOfHandle(me) ?? slot; }
    $: if (data && !chosen && !engine && $myTeam && $myTeam !== me) { me = $myTeam; slot = seatOfHandle(me) ?? slot; }

    // You take the slot you chose; whoever sat there takes your old one.
    $: seating = (() => {
        if (!data) return [];
        const order = [...seatHandles];
        const from = me ? order.indexOf(me) : -1;
        if (from >= 0 && slot - 1 !== from) [order[from], order[slot - 1]] = [order[slot - 1], order[from]];
        return order;
    })();

    function start() {
        clearTimeout(timer);
        results = null;
        const league = {
            ...data.league,
            mySlot: me ? slot : 99,
            adpSource: 'sleeper',
            year: Number(String(data.built).slice(0, 4)),
            seed: Math.floor(Math.random() * 1e9),
            teamNames: seating.map(nameOf),
            tradedPicks: null,
            teamProfiles: seating.map(profileOf),
        };
        const cpu = { ...DEFAULT_CPU, useManagerProfiles: room === 'managers' };
        engine = createDraft(league, cpu, data.players, null, []);
        tick();
    }

    // Computer seats pick on a short timer so you can watch the room move.
    function tick() {
        clearTimeout(timer);
        if (!engine) return;
        if (engine.state.done) { results = gradeDraft(engine); return; }
        if (currentTeam(engine.state)?.isUser) return;
        engine = runCpuPick(engine);
        timer = setTimeout(tick, PACE_MS);
    }
    function take(id) {
        if (!onClock) return;
        engine = draftPlayer(engine, id);
        timer = setTimeout(tick, PACE_MS);
    }
    function skipToMe() {
        clearTimeout(timer);
        while (engine && !engine.state.done && !currentTeam(engine.state)?.isUser) engine = runCpuPick(engine);
        if (engine.state.done) results = gradeDraft(engine);
    }
    function finishForMe() {
        clearTimeout(timer);
        engine = autoDraftRest(engine);
        results = gradeDraft(engine);
    }
    function reset() { clearTimeout(timer); engine = null; results = null; }

    $: st = engine?.state;
    $: onClock = !!st && !st.done && !!currentTeam(st)?.isUser;
    $: pickNo = st ? currentPick(st) : 0;
    $: teams = data?.league.teams || 12;
    $: label = (n) => `${Math.ceil(n / teams)}.${String(((n - 1) % teams) + 1).padStart(2, '0')}`;
    $: clockTeam = st && !st.done ? currentTeam(st) : null;
    $: myNext = st && !st.done ? nextUserPick(st, onClock ? pickNo + 1 : pickNo) : null;
    $: pool = engine ? availablePlayers(engine)
        .filter((p) => posFilter === 'ALL' || p.position === posFilter)
        .filter((p) => !search || p.name.toLowerCase().includes(search.toLowerCase()))
        .slice(0, 60) : [];
    $: cells = (() => {
        const m = new Map();
        if (st) for (const p of st.picks) m.set(`${p.round}-${p.teamIndex}`, engine.byId.get(p.playerId));
        return m;
    })();
    $: myTeamState = st ? st.teams.find((t) => t.isUser) : null;
    $: myPlayers = engine && myTeamState ? playersOf(engine, myTeamState) : [];
    $: myResult = results ? results.find((r) => r.team.isUser) : null;
    const lasts = (p) => (myNext ? Math.round(survivalOdds(p, pickNo, myNext) * 100) : null);

    // Read-outs beside the board.
    let showHow = false;
    let sim = null, simKey = '';
    const pct = (x) => `${Math.round(x * 100)}%`;
    $: round = st ? Math.min(data.league.rounds, Math.ceil(pickNo / teams)) : 1;
    $: winStart = onClock ? pickNo + 1 : pickNo;
    $: windowPicks = st && myNext
        ? Array.from({ length: Math.max(0, myNext - winStart) }, (_, k) => winStart + k)
            .map((o) => ({ o, team: st.teams[st.order[o - 1]] }))
            .filter((x) => !x.team.isUser)
        : [];
    // A team at the turn picks twice in a row; show it once with both picks.
    $: windowTeams = (() => {
        const m = new Map();
        for (const w of windowPicks) {
            if (!m.has(w.team.index)) m.set(w.team.index, { team: w.team, picks: [] });
            m.get(w.team.index).picks.push(w.o);
        }
        return [...m.values()];
    })();
    $: availAll = engine ? availablePlayers(engine) : [];
    $: topByPos = ['QB', 'RB', 'WR', 'TE'].map((p) => availAll.find((x) => x.position === p)).filter(Boolean);
    // The odds only matter when the pick is yours, so the runs happen then.
    $: if (engine && onClock && myNext) {
        const key = `${engine.state.league.seed}-${pickNo}`;
        if (key !== simKey) {
            simKey = key; sim = null;
            const e = engine, until = myNext;
            setTimeout(() => { if (engine === e) sim = { at: currentPick(e.state), ...simulateWindow(e, until) }; }, 30);
        }
    }
    // Odds from an earlier turn describe a board that no longer exists.
    $: liveSim = sim && onClock && sim.at === pickNo ? sim : null;
    $: if (!engine) { sim = null; simKey = ''; }
    $: area = data && st ? areaMix(data.roundMix, data.players, teams, round, Math.min(data.league.rounds, round + 2)) : null;
    const gradeColor = (g) => g.startsWith('A') ? '#27ae60' : g.startsWith('B') ? '#2980b9' : g.startsWith('C') ? '#7f8c8d' : g.startsWith('D') ? '#e67e22' : '#c0392b';
</script>

<svelte:head><title>Mock Draft</title></svelte:head>

<div class="holder">
    <h1>Mock Draft</h1>
    {#if error}
        <p class="sub">{error}</p>
    {:else if !data}
        <p class="sub">Loading the draft room…</p>
    {:else if !engine}
        <p class="sub">Every other seat drafts the way its manager really has in this league: when he takes his first quarterback and tight end, how many he carries, what he takes in round one, and the players he keeps coming back to. Built from {data.profileDrafts.length} FL Players drafts, {data.profileDrafts[0].season} to {data.profileDrafts[data.profileDrafts.length - 1].season}.</p>

        <section class="setup">
            <label>
                <span>You are</span>
                <select value={me || ''} on:change={(e) => pickMe(e.target.value)}>
                    <option value="">Nobody, just watch</option>
                    {#each managersList as h}<option value={h}>{nameOf(h)}</option>{/each}
                </select>
            </label>
            {#if me}
                <label>
                    <span>Your draft slot</span>
                    <select bind:value={slot}>
                        {#each seatHandles as _, i}<option value={i + 1}>{i + 1}</option>{/each}
                    </select>
                </label>
            {/if}
            <label>
                <span>The room</span>
                <select bind:value={room}>
                    <option value="managers">Drafts like the real managers</option>
                    <option value="adp">Drafts straight off ADP</option>
                </select>
            </label>
            <button class="go" on:click={start} disabled={adpChecking}>{adpChecking ? 'Reading live ADP…' : 'Start the draft'}</button>
        </section>
        <p class="note">{data.league.teams} teams, {data.league.rounds} rounds, snake, half PPR. Seats start in last year's draft order. {#if adpLive}ADP live from Sleeper ({adpLive.season} season, {adpLive.ranked} players ranked, read just now){:else if adpChecking}Reading live ADP from Sleeper…{:else}Live ADP unavailable, so this uses the Sleeper snapshot from {data.built}{/if}. Draft-position spread from <a href="https://fantasyfootballcalculator.com" target="_blank" rel="noopener">Fantasy Football Calculator</a>.</p>

        <button class="link" on:click={() => (showHow = !showHow)}>{showHow ? 'Hide' : 'Show'} how this mock works</button>
        {#if showHow}
            <div class="md-how">
                <div>
                    <h3>The board</h3>
                    <p>Players are ranked by Sleeper's current half PPR ADP, read in your browser every time this page opens. When Sleeper rolls over to next season, the board follows it. If Sleeper can't be reached, the page falls back to a saved copy and says so above.</p>
                </div>
                <div>
                    <h3>How far players move</h3>
                    <p>Nobody goes exactly at ADP. Each player gets a spread measured from thousands of real drafts by Fantasy Football Calculator, so a guy with a tight ADP stays put and a volatile one can slide or jump. The "lasts" number on the player list comes from the same spread.</p>
                </div>
                <div>
                    <h3>The other eleven seats</h3>
                    <p>Each seat drafts like its manager really has in this league, from every FL Players draft on Sleeper since 2021. Recent drafts count more than old ones. What carries over: the round he takes his first QB and TE (and no earlier than he has in his recent drafts), how many of each he carries, whether he leans RB or WR early, what he takes in round one, and the players he keeps drafting year after year. Pick "Drafts straight off ADP" to turn all of that off.</p>
                </div>
                <div>
                    <h3>How a computer pick is made</h3>
                    <p>Every pick starts from ADP, adds a roll of the dice sized by that player's spread, then adjusts for what the roster still needs and for that manager's habits. The best score left gets drafted.</p>
                </div>
                <div>
                    <h3>The cards during the draft</h3>
                    <p>"Before you're up again" lists everyone who picks before your next turn, what starting spots they still have open, and where they usually are by now. When you're on the clock it plays that stretch out over a hundred times to show who each team likely takes and how often the best player at each position is still there. "Rounds" compares what this league really took in this part of the draft with what today's ADP would hand out.</p>
                </div>
                <div>
                    <h3>The grades</h3>
                    <p>After the last pick, each roster's best starting lineup is scored on projected season points and ranked against the room. Value counts picks gained or lost against ADP. It's a projection, not a result.</p>
                </div>
                <div>
                    <h3>What it doesn't know</h3>
                    <p>News, injuries and depth charts only show up as far as ADP has already moved. Draft habits from your other leagues aren't in yet; each seat only knows how its manager drafts here.</p>
                </div>
            </div>
        {/if}
        <button class="link" on:click={() => (showHabits = !showHabits)}>{showHabits ? 'Hide' : 'Show'} how each manager drafts</button>
        {#if showHabits}
            <div class="md-habits">
                {#each seating as h, i}
                    <div class="md-habit" class:mine={ready && h === me}>
                        <span class="seat">{i + 1}</span>
                        <b>{nameOf(h)}</b>
                        <small>{profileOf(h) ? describeProfile(profileOf(h)) : 'No draft history, drafts the board'}</small>
                    </div>
                {/each}
            </div>
        {/if}
    {:else}
        <div class="clock" class:yours={onClock}>
            {#if results}
                <b>Draft complete.</b>
            {:else if onClock}
                <b>You're on the clock, pick {label(pickNo)}.</b>
            {:else}
                <span>Pick {label(pickNo)}: <b>{clockTeam?.name}</b> is choosing…</span>
                {#if myNext}<small>Your next pick: {label(myNext)}</small>{/if}
            {/if}
            <span class="actions">
                {#if !results && me && !onClock}<button on:click={skipToMe}>Skip to my pick</button>{/if}
                {#if !results}<button on:click={finishForMe}>Finish it for me</button>{/if}
                <button on:click={start}>Restart</button>
                <button on:click={reset}>Change setup</button>
            </span>
        </div>

        {#if results}
            {#if myResult}
                <div class="mygrade">
                    <span class="letter big" style="background:{gradeColor(myResult.grade)}">{myResult.grade}</span>
                    <div>
                        <b>Your draft ranks {myResult.rank} of {results.length}</b> on projected starting points ({Math.round(myResult.points)}).
                        <small>{myResult.value > 0 ? '+' : ''}{Math.round(myResult.value)} picks of value against ADP · {myResult.byeClashes} starter bye clash{myResult.byeClashes === 1 ? '' : 'es'}</small>
                        <small>Starters: {myResult.starters.map((p) => p.name).join(', ')}</small>
                    </div>
                </div>
            {/if}
            <h2>How the room graded out</h2>
            <p class="note">The letter ranks each roster's projected starting points against the room. Value is picks gained against ADP. A projection, not a result.</p>
            <div class="md-grades">
                {#each results as r}
                    {@const h = seating[r.team.index]}
                    <div class="md-grade" class:mine={r.team.isUser}>
                        <span class="letter" style="background:{gradeColor(r.grade)}">{r.grade}</span>
                        <span>{#if managerLink(h)}<a href={managerLink(h)}>{nameOf(h)}</a>{:else}{nameOf(h)}{/if}</span>
                        <small>{Math.round(r.points)} pts · {r.value > 0 ? '+' : ''}{Math.round(r.value)} value</small>
                    </div>
                {/each}
            </div>
        {/if}

        {#if !results && me && myNext}
            <div class="md-cards">
                <section class="md-card">
                    <h3>Before you're up again <small>{windowPicks.length} pick{windowPicks.length === 1 ? '' : 's'}, your next is {label(myNext)}</small></h3>
                    {#each windowTeams as w (w.team.index)}
                        {@const h = seating[w.team.index]}
                        {@const prof = room === 'managers' ? profileOf(h) : null}
                        {@const needs = openNeeds(w.team.counts, data.league.roster, round, data.league.rounds)}
                        {@const habit = room === 'managers' ? habitNow(prof, w.team.counts, Math.ceil(w.picks[0] / teams)) : ''}
                        {@const fav = room === 'managers' ? repeatsAvailable(prof, engine).filter((f) => (engine.byId.get(f.id)?.adp ?? 999) <= myNext + teams).slice(0, 2) : []}
                        <div class="md-who">
                            <span class="at">{w.picks.map(label).join(' ')}</span>
                            <div>
                                <b>{nameOf(h)}</b>
                                <span class="needs">needs {#each needs as n}<span class="pos {n}">{n}</span>{:else}<i>depth only</i>{/each}</span>
                                {#if habit}<small>{habit}</small>{/if}
                                {#if fav.length}<small>His guys still here: {fav.map((f) => f.label).join(', ')}</small>{/if}
                                {#if liveSim}
                                    {@const ln = liveSim.lean(w.team.index, w.picks.length)}
                                    {#if ln.length}<small class="lean">{w.picks.length > 1 ? 'Each pick likely' : 'Likely takes'} {ln.map((x) => `${x.p} ${pct(x.share)}`).join(' · ')}</small>{/if}
                                {/if}
                            </div>
                        </div>
                    {:else}
                        <p class="note">You pick again right away.</p>
                    {/each}
                    {#if windowPicks.length}
                        <div class="md-risk">
                            {#if liveSim}
                                <small>If you pass on him now, the chance he's still there at {label(myNext)} ({liveSim.runs} runs of this stretch):</small>
                                {#each topByPos as p}
                                    {@const s = liveSim.survives(p.id)}
                                    <div class="md-riskrow"><span class="pos {p.position}">{p.position}</span><span>{p.name}</span><b class:low={s < 0.35} class:high={s >= 0.7}>{pct(s)}</b><small>{liveSim.expected[p.position].toFixed(1)} {p.position} go</small></div>
                                {/each}
                            {:else if onClock}
                                <small>Running this stretch…</small>
                            {:else}
                                <small>The odds run when you're on the clock.</small>
                            {/if}
                        </div>
                    {/if}
                </section>

                {#if area}
                    <section class="md-card">
                        <h3>{area.toRound > area.fromRound ? `Rounds ${area.fromRound} to ${area.toRound}` : `Round ${area.fromRound}`} in FL Players <small>real picks, {area.seasons[0]} to {area.seasons[area.seasons.length - 1]}, against today's ADP</small></h3>
                        {#each area.rows as r}
                            <div class="md-bar">
                                <span class="pos {r.p}">{r.p}</span>
                                <span class="track"><span class="real {r.p}" style="width:{r.real * 100}%"></span><span class="adpmark" style="left:{r.adp * 100}%"></span></span>
                                <b>{pct(r.real)}</b><small>ADP {pct(r.adp)}</small>
                            </div>
                        {/each}
                        <p class="note left">{#if area.gap && Math.abs(area.gap.real - area.gap.adp) >= 0.06}This league takes {area.gap.p} {area.gap.real > area.gap.adp ? 'more' : 'less'} often here than ADP says ({pct(area.gap.real)} against {pct(area.gap.adp)}).{:else}This league drafts close to ADP in this stretch.{/if} The bar is what the league really took; the line is today's board.</p>
                    </section>
                {/if}
            </div>
        {/if}

        <div class="room" class:done={!!results}>
            {#if !results}
                <section class="pool">
                    <div class="filters">
                        {#each ['ALL', ...POS] as p}
                            <button class="chip" class:on={posFilter === p} on:click={() => (posFilter = p)}>{p}</button>
                        {/each}
                        <input type="search" placeholder="Find a player" bind:value={search} />
                    </div>
                    <div class="md-list">
                        {#each pool as p (p.id)}
                            <div class="md-row">
                                <span class="pos {p.position}">{p.position}</span>
                                <span class="who"><b>{p.name}</b><small>{p.team || 'FA'}{p.bye ? ` · bye ${p.bye}` : ''}</small></span>
                                <span class="num"><b>{p.adp.toFixed(1)}</b><small>ADP</small></span>
                                {#if lasts(p) != null}<span class="num"><b>{lasts(p)}%</b><small>lasts</small></span>{/if}
                                {#if onClock}<button class="take" on:click={() => take(p.id)}>Draft</button>{/if}
                            </div>
                        {/each}
                    </div>
                    <p class="note">"Lasts" is the chance he's still there at your next pick, from how far players at his ADP really move.</p>
                </section>
            {/if}

            <section class="boardwrap">
                <div class="md-board" style="grid-template-columns: 2.4em repeat({teams}, minmax(6.2em, 1fr));">
                    <span></span>
                    {#each seating as h, i}
                        <span class="md-head" class:mine={st.teams[i].isUser} title={profileOf(h) ? describeProfile(profileOf(h)) : ''}>{nameOf(h)}</span>
                    {/each}
                    {#each Array(data.league.rounds) as _, r}
                        <span class="rnd">{r + 1}</span>
                        {#each seating as _h, i}
                            {@const pl = cells.get(`${r + 1}-${i}`)}
                            <span class="md-cell {pl ? pl.position : ''}" class:mine={st.teams[i].isUser}>
                                {#if pl}<b>{pl.name}</b><small>{pl.position} · {pl.team || 'FA'}</small>{/if}
                            </span>
                        {/each}
                    {/each}
                </div>
            </section>

            {#if !results && me}
                <section class="mine-list">
                    <h3>Your team</h3>
                    {#each POS as p}
                        {@const ps = myPlayers.filter((x) => x.position === p)}
                        <div class="md-slot"><span class="pos {p}">{p}</span>{ps.length ? ps.map((x) => x.name).join(', ') : '–'}</div>
                    {/each}
                </section>
            {/if}
        </div>
    {/if}
</div>

<style>
    .holder { max-width: 1280px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h2 { margin-top: 1.4em; font-size: 1.15em; border-bottom: 1px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; }
    h3 { font-size: 1em; margin: 0 0 0.4em; }
    .note a { color: inherit; text-decoration: underline; }
    .sub, .note { text-align: center; opacity: 0.78; font-size: 0.92em; line-height: 1.5; max-width: 760px; margin-left: auto; margin-right: auto; }
    button { font: inherit; cursor: pointer; border: 1px solid rgba(127,127,127,0.45); background: transparent; color: inherit; border-radius: 6px; padding: 0.35em 0.75em; }
    button:hover { border-color: #27ae60; }
    select, input { font: inherit; padding: 0.3em 0.5em; }

    .setup { display: flex; flex-wrap: wrap; gap: 1em; justify-content: center; align-items: flex-end; margin: 1.2em 0 0.4em; }
    .setup label { display: flex; flex-direction: column; gap: 0.25em; font-size: 0.85em; }
    .setup label span { opacity: 0.75; }
    .go { background: #27ae60; border-color: #27ae60; color: #fff; font-weight: 700; padding: 0.5em 1.2em; }
    .link { display: block; margin: 1em auto 0; border: none; text-decoration: underline; opacity: 0.8; }
    .md-habits { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.5em; margin-top: 0.8em; }
    .md-habit { display: grid; grid-template-columns: 2em 1fr; column-gap: 0.5em; border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.45em 0.6em; }
    .md-habit .seat { grid-row: span 2; font-weight: 800; opacity: 0.6; align-self: center; text-align: center; }
    .md-habit small { opacity: 0.75; font-size: 0.8em; line-height: 1.35; }
    .mine { border-color: #27ae60 !important; background: rgba(39,174,96,0.12); }

    .clock { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4em 1em; border: 1px solid rgba(127,127,127,0.35); border-radius: 8px; padding: 0.6em 0.9em; margin: 1em 0; position: sticky; top: 0; z-index: 3; background: rgba(127,127,127,0.22); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
    .clock.yours { border-color: #27ae60; box-shadow: 0 0 0 2px rgba(39,174,96,0.35); }
    .clock small { opacity: 0.7; }
    .actions { margin-left: auto; display: flex; gap: 0.4em; flex-wrap: wrap; }

    /* Board across the top so all twelve teams show at once, players and your
       roster underneath, the way Sleeper lays out its own draft room. */
    .room { display: grid; grid-template-columns: minmax(0, 1fr) 230px; grid-template-areas: "board board" "pool mine"; gap: 1em; align-items: start; }
    .room.done { grid-template-columns: minmax(0, 1fr); grid-template-areas: "board"; }
    .boardwrap { grid-area: board; }
    .pool { grid-area: pool; min-width: 0; }
    .mine-list { grid-area: mine; position: sticky; top: 5em; }
    @media (max-width: 760px) {
        .room { grid-template-columns: minmax(0, 1fr); grid-template-areas: "board" "mine" "pool"; }
        .mine-list { position: static; }
    }

    .filters { display: flex; flex-wrap: wrap; gap: 0.3em; margin-bottom: 0.5em; }
    .filters input { flex: 1 1 100%; margin-top: 0.2em; }
    .chip { padding: 0.15em 0.55em; font-size: 0.8em; }
    .chip.on { background: #27ae60; border-color: #27ae60; color: #fff; }
    .md-list { max-height: 60vh; overflow-y: auto; border: 1px solid rgba(127,127,127,0.25); border-radius: 8px; }
    .md-row { display: flex; align-items: center; gap: 0.5em; padding: 0.35em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.15); font-size: 0.88em; }
    .who { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .who b { line-height: 1.2; }
    .who small, .num small { opacity: 0.65; font-size: 0.78em; }
    .num { display: flex; flex-direction: column; align-items: flex-end; font-variant-numeric: tabular-nums; min-width: 2.8em; }
    .take { background: #27ae60; border-color: #27ae60; color: #fff; font-weight: 700; padding: 0.2em 0.6em; }

    .pos { display: inline-block; min-width: 2.6em; text-align: center; color: #fff; font-weight: 700; font-size: 0.72em; border-radius: 4px; padding: 0.15em 0.2em; }
    .QB { background: #c0392b; } .RB { background: #1e8449; } .WR { background: #2471a3; }
    .TE { background: #ca6f1e; } .K { background: #7d3c98; } .DEF { background: #566573; }

    .boardwrap { overflow: auto; max-height: 52vh; border: 1px solid rgba(127,127,127,0.25); border-radius: 8px; }
    .done .boardwrap { max-height: none; }
    .md-board { display: grid; gap: 2px; padding: 2px; font-size: 0.74em; }
    .md-board > * { min-width: 0; }
    .md-head { font-weight: 700; padding: 0.3em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-bottom: 2px solid rgba(127,127,127,0.35); max-width: 9em; position: sticky; top: 0; z-index: 1; background: rgba(127,127,127,0.3); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
    .rnd { opacity: 0.6; font-weight: 700; align-self: center; text-align: center; }
    .md-cell { min-height: 2.3em; border-radius: 4px; padding: 0.2em 0.35em; display: flex; flex-direction: column; justify-content: center; background: rgba(127,127,127,0.08); border: 1px solid transparent; }
    .md-cell.QB, .md-cell.RB, .md-cell.WR, .md-cell.TE, .md-cell.K, .md-cell.DEF { color: #fff; }
    .md-cell.QB { background: #c0392b; } .md-cell.RB { background: #1e8449; } .md-cell.WR { background: #2471a3; }
    .md-cell.TE { background: #ca6f1e; } .md-cell.K { background: #7d3c98; } .md-cell.DEF { background: #566573; }
    .md-cell b, .md-cell small { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .md-cell small { opacity: 0.85; font-size: 0.85em; }
    .md-cell.mine { border: 2px solid #27ae60; }

    .mine-list { border: 1px solid rgba(127,127,127,0.25); border-radius: 8px; padding: 0.6em; font-size: 0.85em; }
    .md-slot { display: flex; gap: 0.5em; align-items: baseline; padding: 0.2em 0; }

    .mygrade { display: flex; gap: 1em; align-items: center; border: 1px solid #27ae60; background: rgba(39,174,96,0.12); border-radius: 8px; padding: 0.8em 1em; }
    .mygrade div { display: flex; flex-direction: column; gap: 0.2em; }
    .mygrade small { opacity: 0.8; }
    .md-grades { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.5em; margin: 0.8em 0 1.2em; }
    .md-grade { display: grid; grid-template-columns: 2.6em 1fr; grid-template-rows: auto auto; column-gap: 0.6em; align-items: center; border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.4em 0.6em; }
    .md-grade a { color: inherit; font-weight: 600; }
    .md-grade small { opacity: 0.7; font-size: 0.78em; }
    .letter { grid-row: span 2; color: #fff; font-weight: 800; text-align: center; border-radius: 6px; padding: 0.35em 0; }
    .letter.big { font-size: 1.8em; padding: 0.2em 0.5em; }

    .md-how { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 0.6em; margin: 0.8em 0; }
    .md-how > div { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.6em 0.8em; }
    .md-how p { margin: 0; font-size: 0.88em; line-height: 1.5; opacity: 0.85; }

    .md-cards { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr); gap: 1em; margin-bottom: 1em; align-items: start; }
    @media (max-width: 760px) { .md-cards { grid-template-columns: minmax(0, 1fr); } }
    .md-card { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.6em 0.8em; font-size: 0.86em; }
    .md-card h3 small { display: block; font-weight: 400; opacity: 0.65; font-size: 0.82em; }
    .md-who { display: grid; grid-template-columns: 3em 1fr; gap: 0.5em; padding: 0.35em 0; border-top: 1px solid rgba(127,127,127,0.15); }
    .md-who .at { font-weight: 800; opacity: 0.6; font-variant-numeric: tabular-nums; }
    .md-who div { display: flex; flex-direction: column; gap: 0.15em; }
    .md-who small { opacity: 0.75; line-height: 1.35; }
    .md-who .lean { opacity: 0.95; font-weight: 600; }
    .needs { font-size: 0.85em; opacity: 0.85; display: flex; flex-wrap: wrap; gap: 0.25em; align-items: center; }
    .md-risk { border-top: 1px solid rgba(127,127,127,0.3); margin-top: 0.4em; padding-top: 0.4em; display: flex; flex-direction: column; gap: 0.25em; }
    .md-risk > small { opacity: 0.75; }
    .md-riskrow { display: grid; grid-template-columns: 3em 1fr 3em 5.5em; gap: 0.5em; align-items: center; }
    .md-riskrow b { text-align: right; font-variant-numeric: tabular-nums; }
    .md-riskrow b.low { color: #e74c3c; } .md-riskrow b.high { color: #2ecc71; }
    .md-riskrow small { opacity: 0.65; }
    .md-bar { display: grid; grid-template-columns: 3em 1fr 2.8em 4.2em; gap: 0.5em; align-items: center; padding: 0.15em 0; }
    .md-bar b { text-align: right; font-variant-numeric: tabular-nums; }
    .md-bar small { opacity: 0.65; }
    .track { position: relative; height: 0.7em; background: rgba(127,127,127,0.18); border-radius: 4px; }
    .track .real { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; }
    .track .adpmark { position: absolute; top: -0.2em; bottom: -0.2em; width: 2px; background: currentColor; }
    .note.left { text-align: left; margin: 0.5em 0 0; }
</style>
