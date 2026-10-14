<script>
    import TimelineChart from '$lib/Timeline/TimelineChart.svelte';
    import { recapBySlug, videoEmbed } from '$lib/utils/recaps';
    import { onMount } from 'svelte';
    import { nameOf, slugFor, site } from '$lib/utils/flpHistory';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import WeekAwards from '$lib/Charts/WeekAwards.svelte';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';
    import { myTeam } from '$lib/utils/myTeam';
    import NewsletterIssue from '$lib/Newsletter/NewsletterIssue.svelte';
    import { newsletterFor } from '$lib/utils/newsletters';
    let ready = false;
    onMount(() => { ready = true; });
    export let data;

    // The message to paste in the league chat: the week's headline awards and
    // a link back to this issue. Built from the data, so it exists every week
    // whether or not the issue has a written lead.
    const SHARE_KEYS = ['high', 'top_player', 'closest', 'blowout', 'bench', 'unlucky'];
    let copied = false, canShare = false;
    onMount(() => { canShare = typeof navigator !== 'undefined' && !!navigator.share; });
    $: issueUrl = ready && r ? `${location.origin}/recaps/${r.slug}` : '';
    $: shareText = r ? [
        nl ? `${nl.masthead}, week ${r.week}: ${nl.headline}` : `${site.league_name}, week ${r.week} newsletter`,
        ...(nl?.dek ? [nl.dek] : r.intro ? [r.intro.split(/(?<=[.!?])\s/)[0]] : []),
        '',
        ...SHARE_KEYS.map((k) => (r.awards || []).find((a) => a.key === k)).filter(Boolean).map((a) =>
            `${a.emoji} ${a.name}: ${nameOf(a.manager)}${a.vs ? ` over ${nameOf(a.vs)}` : ''}, ${a.value}${a.note && a.key === 'top_player' ? ` (${a.note})` : ''}`),
        '',
        `Read it: ${issueUrl}`,
    ].join('\n') : '';
    async function copyShare() {
        try { await navigator.clipboard.writeText(shareText); copied = true; setTimeout(() => (copied = false), 2000); }
        catch { copied = false; }
    }
    async function nativeShare() {
        try { await navigator.share({ title: `${site.league_name} week ${r.week} newsletter`, text: shareText }); } catch { /* cancelled */ }
    }

    $: r = recapBySlug(data.slug);
    $: nl = r ? newsletterFor(r.slug) : null;
    $: v = r && videoEmbed(r.video);
    $: paras = (r?.intro || '').split(/\n\s*\n/).filter(Boolean);
    $: scoreBars = (r?.scores || []).map(s => ({
        label: nameOf(s.manager), value: s.points,
        note: s.optimal > s.points ? `best ${s.optimal}` : 'perfect lineup',
        highlight: ready && s.manager === $myTeam,
    }));
    $: benchBars = (r?.scores || []).map(s => ({
        label: nameOf(s.manager), value: Math.round((s.optimal - s.points) * 100) / 100,
        color: '#e67e22', highlight: ready && s.manager === $myTeam,
    })).sort((a, b) => b.value - a.value);
    $: games = r ? [...r.games].sort((a, b) =>
        (ready && [b.winner.manager, b.loser.manager].includes($myTeam)) - (ready && [a.winner.manager, a.loser.manager].includes($myTeam))) : [];
    // a team on bye (13-team League Bound) has no matchup card; its story goes after them
    $: byeStories = nl?.managers && r ? nl.managers.filter((m) =>
        !r.games.some((g) => g.winner.manager === m.handle || g.loser.manager === m.handle)) : [];
    const h2h = (g) => {
        const [w, l] = g.h2h_before;
        if (!w && !l) return 'First ever meeting';
        if (w === l) return `All-time series was tied ${w}–${l} going in`;
        const leader = w > l ? g.winner.manager : g.loser.manager;
        return `${nameOf(leader)} led the all-time series ${Math.max(w, l)}–${Math.min(w, l)} going in`;
    };
</script>

<svelte:head><title>{r ? `${r.season} week ${r.week} newsletter` : 'Newsletter'} | {site.league_name}</title></svelte:head>

<div class="holder">
    <p class="back"><a href="/recaps">← Every issue</a></p>
    {#if !r}
        <h1>Recap not found</h1>
    {:else}
        {@const f = r.facts}
        <h1>{r.season} · Week {r.week} newsletter</h1>

        {#if v}
            <div class="video">
                {#if v.kind === 'iframe'}
                    <iframe src={v.src} title="{r.title} video" allow="accelerometer; encrypted-media; picture-in-picture; fullscreen" allowfullscreen loading="lazy"></iframe>
                {:else if v.kind === 'video'}
                    <!-- svelte-ignore a11y_media_has_caption -->
                    <video src={v.src} controls preload="metadata"></video>
                {:else}
                    <p><a href={v.src} target="_blank" rel="noopener">Watch this week's video →</a></p>
                {/if}
            </div>
        {/if}

        {#if nl}
            <NewsletterIssue {nl} recap={r} part="top" />
        {:else}
            {#each paras as p}<p class="intro">{p}</p>{/each}
        {/if}

        {#if ready}
            <section class="share">
                <h2>Share this issue</h2>
                <p class="meta">Paste it in the league chat. The link opens this page.</p>
                <textarea readonly rows={shareText.split('\n').length}>{shareText}</textarea>
                <div class="share-actions">
                    <button on:click={copyShare}>{copied ? 'Copied' : 'Copy message'}</button>
                    {#if canShare}<button on:click={nativeShare}>Share…</button>{/if}
                </div>
            </section>
        {/if}

        {#if nl}<h2>The numbers</h2>{/if}
        <WeekAwards awards={r.awards} />

        {#if r.scores?.length}
            <h2>Every score this week</h2>
            <HBarChart items={scoreBars} refLine={{ value: r.median, label: `median ${r.median}` }} ariaLabel="Week {r.week} scores" />
            <h2>Points left on the bench</h2>
            <p class="meta">Best possible lineup minus the lineup that was played.</p>
            <HBarChart items={benchBars} ariaLabel="Week {r.week} points left on the bench" />
        {/if}

        {#if r.notes?.length}
            <h2>Talking points</h2>
            <ul>{#each r.notes as n}<li>{n}</li>{/each}</ul>
        {/if}

        <h2>Every matchup{#if nl} <small class="h2s">and every manager's story</small>{/if}</h2>
        {#each games as g}
            <section class="game" class:mine={ready && [g.winner.manager, g.loser.manager].includes($myTeam)}>
                <h3>
                    <span class="w">{nameOf(g.winner.manager)} {g.winner.points}</span><YourTeamBadge handle={g.winner.manager} size="small" />
                    <span class="d">def.</span>
                    <span>{nameOf(g.loser.manager)} {g.loser.points}</span><YourTeamBadge handle={g.loser.manager} size="small" />
                </h3>
                <p class="meta">
                    {h2h(g)} · <a href="/rivalries/{slugFor(g.winner.manager, g.loser.manager)}">rivalry page</a>
                </p>
                <TimelineChart slots={r.slots}
                    a={{ label: nameOf(g.winner.manager), values: g.winner.timeline }}
                    b={{ label: nameOf(g.loser.manager), values: g.loser.timeline }} />
                <table>
                    <thead><tr><th></th><th>{nameOf(g.winner.manager)}</th><th>{nameOf(g.loser.manager)}</th></tr></thead>
                    <tbody>
                        <tr><td>Best possible lineup</td><td>{g.winner.optimal}</td><td>{g.loser.optimal}</td></tr>
                        <tr><td>Left on the bench</td><td>{g.winner.left_on_bench}</td><td>{g.loser.left_on_bench}</td></tr>
                        <tr><td>Top starter</td><td>{g.winner.top[0]?.name} {g.winner.top[0]?.pts}</td><td>{g.loser.top[0]?.name} {g.loser.top[0]?.pts}</td></tr>
                        <tr><td>Best bench player</td><td>{g.winner.best_bench?.name ?? '—'} {g.winner.best_bench?.pts ?? ''}</td><td>{g.loser.best_bench?.name ?? '—'} {g.loser.best_bench?.pts ?? ''}</td></tr>
                        <tr><td>Lowest starter</td><td>{g.winner.worst_start?.name} {g.winner.worst_start?.pts}</td><td>{g.loser.worst_start?.name} {g.loser.worst_start?.pts}</td></tr>
                    </tbody>
                </table>
                {#if g.loser.optimal > g.winner.points}
                    <p class="what-if">{nameOf(g.loser.manager)}'s best lineup ({g.loser.optimal}) would have won.</p>
                {/if}
                {#if nl?.managers?.length}
                    <div class="stories">
                        <NewsletterIssue {nl} recap={r} part="story" handle={g.winner.manager} />
                        <NewsletterIssue {nl} recap={r} part="story" handle={g.loser.manager} />
                    </div>
                {/if}
            </section>
        {/each}

        {#each byeStories as m (m.handle)}
            <section class="game">
                <h3><span>{nameOf(m.handle)}</span><span class="d">on bye</span></h3>
                <div class="stories one"><NewsletterIssue {nl} recap={r} part="story" handle={m.handle} /></div>
            </section>
        {/each}

        <h2>Standings after week {r.week}</h2>
        <table>
            <thead><tr><th>#</th><th>Manager</th><th>W-L</th><th class="num">PF</th></tr></thead>
            <tbody>
                {#each r.standings as s, i}
                    <tr class:minerow={ready && s.manager === $myTeam}><td>{i + 1}</td><td>{nameOf(s.manager)}<YourTeamBadge handle={s.manager} size="small" /></td><td>{s.w}-{s.l}{s.t ? `-${s.t}` : ''}</td><td class="num">{s.pf}</td></tr>
                {/each}
            </tbody>
        </table>
        {#if nl}<NewsletterIssue {nl} recap={r} part="bottom" />{/if}

        <p class="stamp">Built {r.generated.slice(0, 10)} from Sleeper. Timeline windows use NFL kickoff times.</p>
    {/if}
</div>

<style>
    .holder { max-width: 820px; margin: 0 auto; padding: 1.5em 1em; }
    .back a { color: inherit; opacity: 0.75; }
    h1 { text-align: center; }
    h2 { margin-top: 1.8em; border-bottom: 2px solid rgba(127,127,127,0.3); padding-bottom: 0.2em; font-size: 1.2em; }
    h3 { margin: 0; font-size: 1.05em; display: flex; gap: 0.5em; flex-wrap: wrap; }
    .w { color: #27ae60; }
    .d { opacity: 0.5; font-weight: 400; }
    .video { position: relative; width: 100%; aspect-ratio: 16 / 9; margin: 1em 0; }
    .video iframe, .video video { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; border-radius: 8px; background: #000; }
    .intro { line-height: 1.6; }
    .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.7em; margin-top: 1em; }
    .facts div { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.7em; text-align: center; font-size: 0.92em; }
    .facts span { display: block; font-size: 0.78em; opacity: 0.7; text-transform: uppercase; }
    .facts b { display: block; font-size: 1.15em; }
    .game { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 1em; margin: 1em 0; }
    .game.mine { border-color: #27ae60; box-shadow: inset 4px 0 0 #27ae60; }
    tr.minerow td { background: rgba(39, 174, 96, 0.15); }
    .meta { margin: 0.3em 0 0; opacity: 0.8; font-size: 0.9em; }
    .meta a { color: #3498db; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.4em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.25); text-align: left; font-size: 0.9em; }
    .num { text-align: right; }
    .stories { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8em; margin-top: 0.9em; }
    .stories.one { grid-template-columns: 1fr; }
    @media (max-width: 700px) { .stories { grid-template-columns: 1fr; } }
    .h2s { font-size: 0.7em; font-weight: 400; opacity: 0.7; }
    .what-if { color: #e67e22; font-weight: 600; margin: 0.5em 0 0; }
    .share { border: 1px solid rgba(39,174,96,0.6); border-radius: 8px; padding: 0.8em 1em 1em; margin: 1.2em 0; }
    .share h2 { margin-top: 0; border: none; padding: 0; }
    .share textarea { width: 100%; box-sizing: border-box; font: inherit; font-size: 0.9em; line-height: 1.45; padding: 0.6em; border-radius: 6px; border: 1px solid rgba(127,127,127,0.4); background: rgba(127,127,127,0.08); color: inherit; resize: vertical; }
    .share-actions { display: flex; gap: 0.5em; margin-top: 0.5em; }
    .share-actions button { font: inherit; cursor: pointer; border-radius: 6px; padding: 0.4em 0.9em; border: 1px solid #27ae60; background: #27ae60; color: #fff; font-weight: 700; }
    .share-actions button + button { background: transparent; color: inherit; }
    .stamp { opacity: 0.6; text-align: center; font-size: 0.85em; margin-top: 2em; }
</style>
