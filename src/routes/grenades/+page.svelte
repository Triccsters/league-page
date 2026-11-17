<script>
    // The players who kept getting passed around, and whose owners kept losing.
    // Built by scripts/grenades.py. The wording here matches what that script
    // actually measures: it never claims a player CAUSED a loss.
    import { nameOf, managerLink, site } from '$lib/utils/flpHistory';
    import data from '$lib/data/grenades.json';

    const list = data?.grenades || [];
    const streamed = data?.streamed || [];
    const posMedian = data?.pos_median || {};
    const considered = data?.considered ?? null;

    let pos = 'ALL';
    $: positions = ['ALL', ...[...new Set(list.map((g) => g.pos))].sort()];
    $: shown = pos === 'ALL' ? list : list.filter((g) => g.pos === pos);

    const n1 = (x) => (x == null ? '' : (Math.round(x * 100) / 100).toLocaleString());
    const pct = (x) => (x == null ? '' : Math.round(x * 100) + '%');
</script>

<svelte:head><title>Grenades | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>Grenades</h1>

    {#if !list.length}
        <p class="note">No player in this league has cleared the bar yet. That needs at
            least {data?.min_starts ?? 8} starts across {data?.min_owners ?? 3} different
            managers, and this league may simply not have enough seasons on record.</p>
    {:else}
        <p class="note">A grenade is a player who gets dropped and picked up over and over,
            and whose owner tends to lose the week he starts him. Three things have to be
            true at once: he has been on at least {data.min_owners} rosters, he returns
            less per start than his position does, and his starts came in losses more
            often than chance. Small samples are pulled toward the league's roughly
            {pct(data.base_loss_rate)} base rate, so a player who lost twice in two starts
            is not a grenade.</p>

        <p class="warn">None of this says a player <b>caused</b> a loss. It says he moved
            around a lot, he returned less than his position does, and the lineups he was
            in lost.</p>

        <div class="filters">
            {#each positions as p}
                <button class:on={pos === p} on:click={() => (pos = p)}>{p}</button>
            {/each}
        </div>

        <ol class="list">
            {#each shown as g, i}
                <li>
                    <div class="rank">{i + 1}</div>
                    <div class="who">
                        <b>{g.n}</b>
                        <span class="sp {g.pos}">{g.pos}</span>
                        <small>{g.seasons[0]}{g.seasons.length > 1 ? ' to ' + g.seasons[g.seasons.length - 1] : ''}
                            · {g.owners} managers{g.handoffs ? ', ' + g.handoffs + ' mid-season handoff' + (g.handoffs > 1 ? 's' : '') : ''}</small>
                    </div>
                    <div class="nums">
                        <div class="stat">
                            <em>{pct(g.adj_loss)}</em>
                            <small>loss rate when started</small>
                        </div>
                        <div class="stat">
                            <em>{g.won}-{g.lost}</em>
                            <small>record in his {g.starts} starts</small>
                        </div>
                        <div class="stat">
                            <em>{n1(g.pps)}</em>
                            <small>a start, against {n1(g.pos_median)} for a {g.pos}</small>
                        </div>
                    </div>
                    {#if g.worst}
                        <div class="worst">
                            Worst night: <b>{n1(g.worst.pts)}</b> in week {g.worst.week}, {g.worst.season},
                            started by
                            {#if managerLink(g.worst.h)}
                                <a href={managerLink(g.worst.h)}>{nameOf(g.worst.h)}</a>
                            {:else}{nameOf(g.worst.h)}{/if}
                        </div>
                    {/if}
                </li>
            {/each}
        </ol>

        {#if streamed.length}
            <section class="streamed">
                <h2>Kickers and defences, ranked apart</h2>
                <p class="note">Everyone streams these, so they would fill every slot above
                    and mean nothing. Same measure, their own list.</p>
                <ol class="mini">
                    {#each streamed.slice(0, 10) as g, i}
                        <li><span>{i + 1}</span> <b>{g.n}</b> <span class="sp {g.pos}">{g.pos}</span>
                            <small>{pct(g.adj_loss)} loss rate, {g.won}-{g.lost} in {g.starts} starts,
                                {g.owners} managers</small></li>
                    {/each}
                </ol>
            </section>
        {/if}

        <p class="foot">
            {#if considered}{considered.toLocaleString()} players met the bar; the worst
            {list.length} are above.{/if}{' '}Positional medians this league: {Object.entries(posMedian)
                .map(([p, v]) => p + ' ' + n1(v)).join(' · ')} points a start.
            See also <a href="/waivers">waiver returns</a> and <a href="/players">the player hall of fame</a>.
        </p>
    {/if}
</div>

<style>
    .holder { max-width: 1040px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.3em; }
    .note { opacity: 0.85; line-height: 1.5; margin: 0 auto 0.8em; max-width: 760px; }
    .warn { max-width: 760px; margin: 0 auto 1.2em; padding: 0.6em 0.9em; line-height: 1.45;
        border-left: 3px solid rgba(241, 196, 15, 0.7); background: rgba(241, 196, 15, 0.08);
        border-radius: 0 8px 8px 0; }
    .filters { display: flex; flex-wrap: wrap; gap: 0.4em; justify-content: center; margin-bottom: 1.1em; }
    .filters button { border: 1px solid rgba(127, 127, 127, 0.4); background: transparent;
        color: inherit; border-radius: 999px; padding: 0.25em 0.8em; cursor: pointer; font: inherit; }
    .filters button.on { background: #2980b9; border-color: #2980b9; color: #fff; }
    .list { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.6em; }
    .list li { display: grid; grid-template-columns: 2.2em 1fr; gap: 0.2em 0.6em;
        border: 1px solid rgba(127, 127, 127, 0.28); border-radius: 11px; padding: 0.7em 0.85em; }
    .rank { grid-row: span 3; font-size: 1.3em; opacity: 0.55; text-align: center; }
    .who b { font-size: 1.05em; }
    .who small { display: block; opacity: 0.7; margin-top: 0.15em; }
    .sp { display: inline-block; font-size: 0.72em; padding: 0.1em 0.45em; border-radius: 5px;
        margin-left: 0.4em; vertical-align: middle; }
    .sp.QB { background: #c0392b; color: #fff; }
    .sp.RB { background: #1e8449; color: #fff; }
    .sp.WR { background: #2980b9; color: #fff; }
    .sp.TE { background: #8e44ad; color: #fff; }
    .sp.K  { background: #d68910; color: #fff; }
    .sp.DEF { background: #566573; color: #fff; }
    .nums { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5em;
        margin-top: 0.5em; }
    .stat em { display: block; font-style: normal; font-size: 1.15em; font-weight: 600; }
    .stat small { opacity: 0.7; }
    .worst { margin-top: 0.5em; font-size: 0.93em; opacity: 0.85; }
    .streamed { margin-top: 2em; }
    .mini { list-style: none; padding: 0; display: grid; gap: 0.35em; }
    .mini li { display: flex; align-items: baseline; gap: 0.5em; flex-wrap: wrap;
        border-bottom: 1px solid rgba(127, 127, 127, 0.18); padding-bottom: 0.35em; }
    .mini span:first-child { width: 1.6em; opacity: 0.55; }
    .mini small { opacity: 0.7; }
    .foot { margin-top: 2em; opacity: 0.75; line-height: 1.5; }
</style>
