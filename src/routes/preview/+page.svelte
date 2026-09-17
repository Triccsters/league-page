<script>
    import { onMount } from 'svelte';
    import previews from '$lib/data/previews.json';
    import { nameOf, teamName, slugFor, site, fillNames } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';

    let ready = false;
    onMount(() => { ready = true; });
    $: games = [...previews.games].sort((x, y) =>
        (ready && [y.a, y.b].includes($myTeam)) - (ready && [x.a, x.b].includes($myTeam)));
    const rec = (r) => `${r[0]}-${r[1]}`;
    const lastLine = (g) => {
        const l = g.last;
        if (!l) return 'Never played before';
        const [w, lo] = l.score[g.a] >= l.score[g.b] ? [g.a, g.b] : [g.b, g.a];
        const where = l.label && l.label !== 'Consolation' ? l.label.toLowerCase() : `week ${l.week}`;
        return `Last met in the ${l.season} ${where}: ${nameOf(w)} ${l.score[w]}–${l.score[lo]}`;
    };
</script>

<div class="holder">
    <h1>{previews.week ? `Week ${previews.week} Preview` : 'Week Preview'}</h1>
    {#if !previews.week}
        <p class="sub">No games are scheduled right now. Previews come back when the next week's matchups are set.</p>
    {:else}
        <p class="sub">{previews.playoff ? 'Playoffs. ' : ''}Win chances, head-to-head history and storylines for every {site.season} week {previews.week} game. {previews.note}</p>
        <p class="links"><a href="/odds">Playoff odds →</a> <a href="/timeline">Live timeline →</a></p>
    {/if}

    {#each games as g}
        {@const mine = ready && [g.a, g.b].includes($myTeam)}
        <section class="game" class:mine>
            <div class="teams">
                {#each [g.a, g.b] as h, i}
                    <div class="team" class:right={i === 1}>
                        <b>{nameOf(h)}</b><YourTeamBadge handle={h} size="small" />
                        {#if teamName(site.season, h) && teamName(site.season, h) !== nameOf(h)}<small class="tn">{teamName(site.season, h)}</small>{/if}
                        <small>{rec(g.rec[h])} · averaging {g.avg[h] ?? '—'}</small>
                        {#if g.last3[h]?.length}<small>Recent: {g.last3[h].join(', ')}</small>{/if}
                    </div>
                {/each}
            </div>
            <div class="odds">
                <span class="pa">{g.a_win}%</span>
                <div class="split"><i style="width:{g.a_win}%"></i></div>
                <span class="pb">{(100 - g.a_win).toFixed(1)}%</span>
            </div>
            {#if g.note}
                <div class="writeup">
                    {#each g.note.split('\n').filter(Boolean) as para}<p>{para}</p>{/each}
                </div>
            {/if}
            {#if g.flags.length}
                <ul class="flags">{#each g.flags as f}<li>🔥 {fillNames(f)}</li>{/each}</ul>
            {/if}
            <p class="meta">
                All-time: {nameOf(g.a)} {g.h2h[g.a]}–{g.h2h[g.b]} {nameOf(g.b)} in {g.h2h.games} games · {lastLine(g)} ·
                <a href="/rivalries/{slugFor(g.a, g.b)}">full rivalry</a>
            </p>
        </section>
    {/each}
    <p class="note">Built {previews.generated.slice(0, 10)}. Updated every Tuesday for the week ahead.</p>
</div>

<style>
    .holder { max-width: 820px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub, .note { text-align: center; opacity: 0.75; font-size: 0.92em; }
    .links { text-align: center; display: flex; gap: 1.5em; justify-content: center; }
    .links a, .meta a { color: #3498db; }
    .game { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.9em 1em; margin: 1em 0; }
    .game.mine { border-color: #27ae60; box-shadow: inset 4px 0 0 #27ae60; }
    .teams { display: grid; grid-template-columns: 1fr 1fr; gap: 1em; }
    .team { display: flex; flex-direction: column; }
    .team.right { text-align: right; align-items: flex-end; }
    .team b { font-size: 1.1em; }
    .team small { opacity: 0.7; font-size: 0.8em; }
    .team .tn { font-style: italic; }
    .odds { display: grid; grid-template-columns: 3.5em 1fr 3.5em; align-items: center; gap: 0.5em; margin: 0.6em 0; font-weight: 700; font-variant-numeric: tabular-nums; }
    .pa { color: #3498db; }
    .pb { color: #e74c3c; text-align: right; }
    .split { height: 10px; border-radius: 5px; background: #e74c3c; overflow: hidden; }
    .split i { display: block; height: 100%; background: #3498db; }
    .writeup { margin: 0.5em 0 0.2em; border-left: 3px solid rgba(52,152,219,0.55); padding-left: 0.7em; }
    .writeup p { margin: 0 0 0.4em; font-size: 0.92em; line-height: 1.5; }
    .writeup p:last-child { margin-bottom: 0; }
    .flags { margin: 0.4em 0; padding-left: 0.2em; list-style: none; }
    .flags li { margin: 0.15em 0; font-weight: 600; }
    .meta { margin: 0.3em 0 0; font-size: 0.85em; opacity: 0.8; }
</style>
