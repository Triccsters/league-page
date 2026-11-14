<script>
    // Side challenges for next season. Nothing here is live yet: the page lists the ideas and
    // embeds a Google Form (leagueInfo.challengeForm) so the league can vote. T.J., 2026-11-13.
    import * as leagueInfo from '$lib/utils/leagueInfo';
    const form = leagueInfo.challengeForm || null;
    const embed = form ? (form.includes('embedded=true') ? form : form + (form.includes('?') ? '&' : '?') + 'embedded=true') : null;
    const nextSeason = new Date().getMonth() >= 7 ? new Date().getFullYear() + 1 : new Date().getFullYear();

    const SEASON = [
        { e: '🏝️', n: 'Survivor', r: 'Starting a few weeks in, the lowest score each week is out. Last team standing wins.' },
        { e: '⛰️', n: 'King of the Hill', r: 'The lowest scores each week take a strike. Three strikes and you are out. Last one left is king.' },
        { e: '🗺️', n: 'Conquest', r: 'Everyone starts with one territory on a map. Beat someone and you take a new one plus everything they hold. Most territory at the end wins.' },
        { e: '🤝', n: 'Partners', r: 'Managers are paired up after the draft. A win by either partner counts for the pair. Best pair splits the prize.' },
        { e: '🥇', n: 'Top seeds bonus', r: 'A prize for the top two seeds when the regular season ends, so the regular season pays too.' },
        { e: '📈', n: 'Points title', r: 'A prize for the most points scored in the regular season, whatever the record says.' },
    ];
    const WEEKLY = [
        { e: '🔥', n: 'Weekly high score', r: 'Top score of the week takes a prize, every week of the regular season.' },
        { e: '💔', n: 'Highest losing score', r: 'The best score that still lost. A consolation prize for bad luck.' },
        { e: '📏', n: 'Smallest margin of victory', r: 'The closest win of the week.' },
        { e: '💥', n: 'Biggest blowout', r: 'The largest margin of victory of the week.' },
        { e: '🪑', n: 'Best bench player', r: 'The highest score left on a bench. Painful, but it pays.' },
        { e: '🎯', n: 'Best lineup', r: 'Highest share of your best possible lineup actually started.' },
        { e: '🏈', n: 'Position of the week', r: 'One position each week: the manager who started the top scoring quarterback, running back, receiver, tight end or kicker.' },
        { e: '🃏', n: 'Blackjack', r: 'The team defense closest to 21 points without going over.' },
        { e: '🧤', n: 'Catch them all', r: 'Most receptions by your starters.' },
        { e: '🏃', n: 'Workhorse', r: 'Most rushing attempts by your starters.' },
        { e: '🧊', n: 'Ice cold', r: 'Most starters under 10 points. The prize nobody wants to win.' },
        { e: '🛒', n: 'Best pickup', r: 'The highest scoring player added off waivers that week and started.' },
    ];
</script>

<svelte:head><title>Challenges | {leagueInfo.leagueName || 'League'}</title></svelte:head>

<div class="holder">
    <h1>Challenges</h1>
    <p class="sub">
        Side games for the {nextSeason} season. <b>None of these are running yet.</b> This is the list of ideas, and the
        league decides which ones make it. Prizes are still being worked out.
    </p>

    <h2>Season-long games</h2>
    <p class="lead">One of these would run all year alongside the regular schedule.</p>
    <div class="cards">
        {#each SEASON as c}
            <section class="card"><h3><span>{c.e}</span>{c.n}</h3><p>{c.r}</p></section>
        {/each}
    </div>

    <h2>Weekly challenges</h2>
    <p class="lead">A different one each week, or the same one every week. The site can score all of these on its own.</p>
    <div class="cards">
        {#each WEEKLY as c}
            <section class="card"><h3><span>{c.e}</span>{c.n}</h3><p>{c.r}</p></section>
        {/each}
    </div>

    <h2>Vote</h2>
    {#if embed}
        <p class="lead">Pick the ones you would play. One vote per manager.</p>
        <div class="form"><iframe src={embed} title="Challenge vote" loading="lazy">Loading the form…</iframe></div>
        <p class="lead"><a href={form} target="_blank" rel="noopener">Open the form in its own tab</a></p>
    {:else}
        <p class="lead soon">Voting opens here soon. Until then, tell the commissioner which ones you like.</p>
    {/if}
</div>

<style>
    .holder { max-width: 1000px; margin: 0 auto; padding: 1em; }
    h1 { text-align: center; margin: 0.6em 0 0.2em; }
    h2 { text-align: center; margin: 1.6em 0 0.2em; }
    .sub, .lead { text-align: center; opacity: 0.85; max-width: 720px; margin: 0.2em auto 1em; line-height: 1.5; }
    .lead { font-size: 0.92em; opacity: 0.75; }
    .soon { border: 1px dashed rgba(127,127,127,0.5); border-radius: 10px; padding: 1em; opacity: 0.9; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.8em; }
    .card { border: 1px solid rgba(127,127,127,0.3); border-radius: 12px; padding: 0.8em 1em; background: rgba(127,127,127,0.06); }
    .card h3 { margin: 0 0 0.3em; font-size: 1.05em; display: flex; align-items: center; gap: 0.5em; }
    .card h3 span { font-size: 1.3em; }
    .card p { margin: 0; font-size: 0.92em; line-height: 1.45; opacity: 0.88; }
    .form { max-width: 720px; margin: 0 auto; border-radius: 12px; overflow: hidden; background: #fff; }
    .form iframe { width: 100%; height: 1400px; border: 0; display: block; }
    a { color: inherit; }
</style>
