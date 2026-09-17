<script>
    // Facts the site already knows, in place of the template's blank profile slots.
    import { games, managers, allTimeRank, site } from '$lib/utils/flpHistory';

    export let handle;

    const TITLE = /^Championship$/i;

    function build(h) {
        if (!h || !(h in managers)) return null;
        // record and titles come from the same ranking the All-Time page uses
        const r = allTimeRank(h);
        let finals = 0;
        const seasons = new Set();
        for (const g of games) {
            for (const [me, mp, op] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
                if (me !== h) continue;
                seasons.add(g.season);
                if (g.playoff && TITLE.test(g.label || '')) finals++;
            }
        }
        return {
            rank: r,
            record: r ? `${r.w}-${r.l}` : null,
            titles: r ? r.titles : 0,
            finals,
            seasons: seasons.size,
        };
    }

    $: s = build(handle);
</script>

{#if s && s.record}
    <div class="qs">
        {#if s.rank}
            <span title="All-time rank in the league"><b>#{s.rank.rank}</b> of {s.rank.of}</span>
        {/if}
        <span title="Regular season record"><b>{s.record}</b></span>
        <span title="Seasons played"><b>{s.seasons}</b> {s.seasons === 1 ? 'season' : 'seasons'}</span>
        {#if s.titles}
            <span class="gold" title="Championships">🏆 {s.titles}</span>
        {:else if s.finals}
            <span title="Finals reached, no title yet">🥈 {s.finals}</span>
        {/if}
    </div>
{/if}

<style>
    .qs { display: flex; flex-wrap: wrap; justify-content: center; gap: 0.3em 0.8em;
          font-size: 0.78em; opacity: 0.85; padding: 0.2em 0.4em 0.4em; }
    .qs b { font-weight: 700; }
    .gold { color: #d4a017; }
</style>
