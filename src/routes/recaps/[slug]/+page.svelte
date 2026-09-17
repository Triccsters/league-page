<script>
    import TimelineChart from '$lib/Timeline/TimelineChart.svelte';
    import { recapBySlug, videoEmbed } from '$lib/utils/recaps';
    import { onMount } from 'svelte';
    import { nameOf, slugFor, site } from '$lib/utils/flpHistory';
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import WeekAwards from '$lib/Charts/WeekAwards.svelte';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';
    import { myTeam } from '$lib/utils/myTeam';
    let ready = false;
    onMount(() => { ready = true; });
    export let data;

    $: r = recapBySlug(data.slug);
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
    const h2h = (g) => {
        const [w, l] = g.h2h_before;
        if (!w && !l) return 'First ever meeting';
        if (w === l) return `All-time series was tied ${w}–${l} going in`;
        const leader = w > l ? g.winner.manager : g.loser.manager;
        return `${nameOf(leader)} led the all-time series ${Math.max(w, l)}–${Math.min(w, l)} going in`;
    };
</script>

<svelte:head><title>{r ? `${r.season} ${r.title}` : 'Recap'} | {site.league_name}</title></svelte:head>

<div class="holder">
    <p class="back"><a href="/recaps">← All recaps</a></p>
    {#if !r}
        <h1>Recap not found</h1>
    {:else}
        {@const f = r.facts}
        <h1>{r.season} · {r.title}</h1>

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

        {#each paras as p}<p class="intro">{p}</p>{/each}

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

        <h2>Every matchup</h2>
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
    .what-if { color: #e67e22; font-weight: 600; margin: 0.5em 0 0; }
    .stamp { opacity: 0.6; text-align: center; font-size: 0.85em; margin-top: 2em; }
</style>
