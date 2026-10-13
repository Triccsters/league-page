<script>
    // Standings two ways: head-to-head only, and with a second result each
    // week for finishing above or below the league median. Built from the
    // site's own game log (history.json), so it works on every league site.
    // A league that already plays a median game (odds.json "median": true)
    // opens on that view and the toggle shows the other way.
    import { onMount } from 'svelte';
    import { games, site, nameOf, managerLink } from '$lib/utils/flpHistory';
    import odds from '$lib/data/odds.json';
    import { myTeam } from '$lib/utils/myTeam';

    const leagueHasMedian = !!odds?.median;
    const playoffTeams = odds?.playoff_teams || 6;
    let withMedian = leagueHasMedian;
    let ready = false;
    onMount(() => { ready = true; });

    const season = site.season;
    const played = games.filter((g) => g.season === season && !g.playoff);
    const weeks = [...new Set(played.map((g) => g.week))].sort((a, b) => a - b);

    function median(xs) {
        const s = [...xs].sort((a, b) => a - b);
        const m = Math.floor(s.length / 2);
        return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
    }

    const rec = {};
    const get = (h) => (rec[h] ||= { h, w: 0, l: 0, t: 0, mw: 0, ml: 0, pf: 0 });
    for (const wk of weeks) {
        const gs = played.filter((g) => g.week === wk);
        const med = median(gs.flatMap((g) => [g.pa, g.pb]));
        for (const g of gs) {
            for (const [h, me, them] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
                const r = get(h);
                r.pf += me;
                if (me > them) r.w += 1; else if (me < them) r.l += 1; else r.t += 1;
                if (me > med) r.mw += 1; else if (me < med) r.ml += 1;
            }
        }
    }
    const rows = Object.values(rec);
    const pct = (w, l, t) => (w + l + t ? (w + t / 2) / (w + l + t) : 0);
    const h2hOrder = [...rows].sort((a, b) => pct(b.w, b.l, b.t) - pct(a.w, a.l, a.t) || b.pf - a.pf);
    const medOrder = [...rows].sort((a, b) =>
        pct(b.w + b.mw, b.l + b.ml, b.t) - pct(a.w + a.mw, a.l + a.ml, a.t) || b.pf - a.pf);
    const h2hRank = Object.fromEntries(h2hOrder.map((r, i) => [r.h, i + 1]));
    const medRank = Object.fromEntries(medOrder.map((r, i) => [r.h, i + 1]));

    $: list = withMedian ? medOrder : h2hOrder;
    $: rankOf = withMedian ? medRank : h2hRank;
    // Who crosses the playoff line when the format flips.
    $: movers = rows.filter((r) => (h2hRank[r.h] <= playoffTeams) !== (medRank[r.h] <= playoffTeams));
    const fmt = (w, l, t) => `${w}-${l}${t ? `-${t}` : ''}`;
</script>

{#if weeks.length}
    <section class="msd">
        <h2>What if there was a league median?</h2>
        <p class="sub">
            {#if leagueHasMedian}This league already plays the median: every week is a head-to-head game plus a second win or loss for finishing in the top or bottom half of scoring. Flip it off to see the head-to-head games alone.
            {:else}A median league gives every team a second result each week: a win for scoring in the top half, a loss for the bottom half. It rewards scoring and takes the schedule out of it. Flip it on to see how this season would look.{/if}
        </p>
        <div class="toggle" role="group" aria-label="Standings format">
            <button class:on={!withMedian} on:click={() => (withMedian = false)}>Head-to-head only</button>
            <button class:on={withMedian} on:click={() => (withMedian = true)}>With the median game</button>
        </div>
        <table>
            <thead><tr><th>#</th><th>Manager</th><th>{withMedian ? 'Record with median' : 'Record'}</th><th class="hide-sm">{withMedian ? 'Head-to-head' : 'Top-half weeks'}</th><th class="num">PF</th><th class="num" title="Places the median game moves each team">Median effect</th></tr></thead>
            <tbody>
                {#each list as r, i (r.h)}
                    {@const d = h2hRank[r.h] - medRank[r.h]}
                    <tr class:mine={ready && r.h === $myTeam} class:line={i + 1 === playoffTeams}>
                        <td>{i + 1}</td>
                        <td>{#if managerLink(r.h)}<a href={managerLink(r.h)}>{nameOf(r.h)}</a>{:else}{nameOf(r.h)}{/if}</td>
                        <td>{withMedian ? fmt(r.w + r.mw, r.l + r.ml, r.t) : fmt(r.w, r.l, r.t)}</td>
                        <td class="hide-sm">{withMedian ? fmt(r.w, r.l, r.t) : `${r.mw} of ${r.mw + r.ml}`}</td>
                        <td class="num">{r.pf.toFixed(2)}</td>
                        <td class="num move" class:up={d > 0} class:down={d < 0}>{d > 0 ? `▲${d}` : d < 0 ? `▼${-d}` : '–'}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
        <p class="note">
            Through week {weeks[weeks.length - 1]}, regular season. The line marks the {playoffTeams} playoff spots. "Median effect" is how many places the median game moves each team, up or down.
            {#if movers.length}Changing the format would swap {movers.map((r) => nameOf(r.h)).join(' and ')} across the playoff line.{:else}Nobody crosses the playoff line either way.{/if}
            Every past season, plus strength of schedule, is on <a href="/median">Median &amp; Schedule</a>.
        </p>
    </section>
{/if}

<style>
    .msd { max-width: 820px; margin: 0 auto 4em; padding: 0 1em; text-align: left; }
    h2 { text-align: center; font-size: 1.4em; margin-bottom: 0.3em; }
    .sub, .note { opacity: 0.8; font-size: 0.92em; line-height: 1.5; text-align: center; }
    .toggle { display: flex; justify-content: center; gap: 0; margin: 1em 0; }
    .toggle button { font: inherit; cursor: pointer; padding: 0.45em 1em; border: 1px solid #27ae60; background: transparent; color: inherit; }
    .toggle button:first-child { border-radius: 6px 0 0 6px; }
    .toggle button:last-child { border-radius: 0 6px 6px 0; border-left: none; }
    .toggle button.on { background: #27ae60; color: #fff; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.25); font-size: 0.92em; }
    th { text-align: left; opacity: 0.8; }
    td a { color: inherit; font-weight: 600; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    tr.line td { border-bottom: 2px dashed #27ae60; }
    tr.mine td { background: rgba(39, 174, 96, 0.15); }
    .move.up { color: #2ecc71; font-weight: 700; }
    .move.down { color: #e74c3c; font-weight: 700; }
    @media (max-width: 520px) { .hide-sm { display: none; } }
</style>
