<script>
    // Power rankings, built at the Tuesday update by scripts/power.py:
    // rest-of-season projections in this league's scoring, scoring so far, and
    // all-play record, blended. Dynasty leagues also show roster value.
    import { onMount } from 'svelte';
    import power from '$lib/data/power.json';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import Who from '$lib/Charts/Who.svelte';

    let ready = false, showHow = false;
    onMount(() => { ready = true; });
    const pct = (x) => `${Math.round(x * 100)}%`;
    const ord = (n) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
    $: teams = power?.teams || [];
    $: max = Math.max(...teams.map((t) => t.score), 0.001);
    $: min = Math.min(...teams.map((t) => t.score), 0);
    const width = (s) => `${Math.max(4, ((s - min) / ((max - min) || 1)) * 100)}%`;
    const w = power?.weights || {};
    // "as of" the build date; the board moves every morning with the projections
    const asOf = power?.generated
        ? new Date(power.generated + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
        : 'today';
</script>

{#if teams.length}
    <section class="pb">
        <h2>Power Rankings <small>as of {asOf}, after week {power.through_week}</small></h2>
        <div class="rows">
            {#each teams as t (t.h)}
                {@const mv = t.prev ? t.prev - t.rank : 0}
                <div class="row" class:mine={ready && t.h === $myTeam}>
                    <span class="rk">{t.rank}</span>
                    <span class="mv" class:up={mv > 0} class:down={mv < 0}>{mv > 0 ? `▲${mv}` : mv < 0 ? `▼${-mv}` : ''}</span>
                    <span class="who"><Who h={t.h} /></span>
                    <span class="bar"><span style="width:{width(t.score)}"></span></span>
                    <span class="parts">
                        {#if t.ros_rank}<span title="Projected best lineup per remaining week">ROS {ord(t.ros_rank)}</span>{/if}
                        <span title="Points per game">Pts {ord(t.ppg_rank)}</span>
                        <span title="All-play win %">All-play {pct(t.allplay)}</span>
                        {#if t.dyn_rank}<span class="dyn" title="FantasyPros dynasty roster value">Dynasty {ord(t.dyn_rank)}</span>{/if}
                    </span>
                </div>
            {/each}
        </div>
        <button class="how" on:click={() => (showHow = !showHow)}>{showHow ? 'Hide' : 'How these are ranked'}</button>
        {#if showHow}
            <p class="note">
                {#if w.ros}<b>Rest of season ({pct(w.ros)})</b>: each roster's best lineup for every remaining regular-season week (weeks {power.first_left} to {power.last_left}) on Sleeper's weekly projections, scored with this league's own scoring, byes included. {/if}
                <b>Scoring ({pct(w.ppg)})</b>: points per game this season. <b>All-play ({pct(w.allplay)})</b>: this season's record against every team every week, which takes the schedule out of it.
                {#if power.dynasty}<b>Dynasty</b> is shown, not blended in: roster value from FantasyPros dynasty rankings ({power.dyn_asof}). Who wins this year and who owns the future are different questions.{/if}
                Updated every morning, so this can differ from the rankings in a newsletter issue, which are a snapshot from the day it went out.
            </p>
        {/if}
    </section>
{/if}

<style>
    .pb { max-width: 900px; margin: 1.5em auto; padding: 0 1em; }
    h2 { text-align: center; margin-bottom: 0.6em; }
    h2 small { font-size: 0.6em; font-weight: 400; opacity: 0.7; }
    .rows { display: flex; flex-direction: column; gap: 0.3em; }
    .row { display: grid; grid-template-columns: 1.8em 2.2em minmax(7em, 11em) 1fr auto; align-items: center; gap: 0.5em; padding: 0.35em 0.5em; border: 1px solid rgba(127,127,127,0.25); border-radius: 8px; }
    .row.mine { border-color: #27ae60; background: rgba(39,174,96,0.12); }
    .rk { font-weight: 800; text-align: center; }
    .mv { font-size: 0.75em; font-weight: 700; }
    .mv.up { color: #2ecc71; } .mv.down { color: #e74c3c; }
    .who { font-weight: 700; min-width: 0; overflow: hidden; }
    .who :global(a) { color: inherit; }
    .who :global(.tn) { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .bar { height: 0.7em; background: rgba(127,127,127,0.18); border-radius: 4px; overflow: hidden; }
    .bar span { display: block; height: 100%; background: #27ae60; border-radius: 4px; }
    .parts { display: flex; gap: 0.35em; flex-wrap: wrap; justify-content: flex-end; }
    .parts span { font-size: 0.72em; border: 1px solid rgba(127,127,127,0.4); border-radius: 999px; padding: 0.1em 0.5em; white-space: nowrap; }
    .parts .dyn { border-color: #7d3c98; }
    .how { display: block; margin: 0.8em auto 0; font: inherit; font-size: 0.9em; border: none; background: none; color: inherit; text-decoration: underline; opacity: 0.8; cursor: pointer; }
    .note { opacity: 0.85; font-size: 0.9em; line-height: 1.55; text-align: center; max-width: 760px; margin: 0.5em auto 0; }
    @media (max-width: 640px) {
        .row { grid-template-columns: 1.6em 2em 1fr; }
        .bar { grid-column: 1 / -1; }
        .parts { grid-column: 1 / -1; justify-content: flex-start; }
    }
</style>
