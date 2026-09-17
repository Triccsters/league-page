<script>
    // Season-by-season record and head-to-head for one manager, both eras where the league has them.
    import HBarChart from '$lib/Charts/HBarChart.svelte';
    import { games, nameOf, currentManagers, slugFor, site } from '$lib/utils/flpHistory';
    export let handle;

    const REAL = new Set(['Quarterfinal', 'Semifinal', 'Championship']);

    $: mine = games.filter(g => g.a === handle || g.b === handle).map(g => {
        const me = g.a === handle ? g.pa : g.pb, op = g.a === handle ? g.pb : g.pa;
        return { ...g, me, op, opp: g.a === handle ? g.b : g.a, won: me > op, lost: me < op };
    });

    $: seasons = [...new Set(mine.map(g => g.season))].sort((a, b) => a - b).map(s => {
        const reg = mine.filter(g => g.season === s && !g.playoff);
        const po = mine.filter(g => g.season === s && g.playoff && REAL.has(g.label));
        const final = po.find(g => g.label === 'Championship');
        return {
            s, era: reg[0]?.era || po[0]?.era,
            w: reg.filter(g => g.won).length, l: reg.filter(g => g.lost).length,
            ppg: reg.length ? reg.reduce((t, g) => t + g.me, 0) / reg.length : 0,
            playoffs: po.length > 0, title: !!(final && final.won), final: !!final,
            live: s === site.season,
        };
    });

    $: maxG = Math.max(1, ...seasons.map(s => s.w + s.l));
    const W = 640, H = 200, L = 28, B = 34, T = 14;
    $: bw = (W - L) / Math.max(1, seasons.length);
    $: y = (v) => T + (H - T - B) * (1 - v / maxG);
    const fill = (s) => s.live ? '#27ae60' : s.title ? '#f1c40f' : s.final ? '#8e44ad' : s.playoffs ? '#2980b9' : '#566573';

    $: h2h = currentManagers.filter(o => o !== handle).map(o => {
        const vs = mine.filter(g => g.opp === o && (!g.playoff || REAL.has(g.label)));
        const w = vs.filter(g => g.won).length, l = vs.filter(g => g.lost).length;
        return { label: nameOf(o), value: w - l, note: `${w}-${l}`, href: `/rivalries/${slugFor(handle, o)}` };
    }).filter(r => r.note !== '0-0').sort((a, b) => b.value - a.value);
</script>

{#if seasons.length}
<section class="mh">
    <h3>Season by season</h3>
    <svg viewBox="0 0 {W} {H}" role="img" aria-label="Regular-season wins by season for {nameOf(handle)}">
        <line x1={L} x2={W} y1={y(0)} y2={y(0)} class="axis" />
        <text x={L - 6} y={y(maxG) + 4} class="tick" text-anchor="end">{maxG}</text>
        <text x={L - 6} y={y(0) + 4} class="tick" text-anchor="end">0</text>
        {#each seasons as s, i}
            <rect x={L + i * bw + bw * 0.15} y={y(s.w)} width={bw * 0.7} height={y(0) - y(s.w)} rx="3" fill={fill(s)}>
                <title>{s.s}: {s.w}-{s.l}, {s.ppg.toFixed(1)} pts/game{s.live ? ', season in progress' : s.title ? ', champion' : s.final ? ', lost the final' : s.playoffs ? ', made the playoffs' : ''}</title>
            </rect>
            <text x={L + i * bw + bw / 2} y={y(s.w) - 3} class="lbl" text-anchor="middle">{s.w}-{s.l}{s.live ? '*' : ''}</text>
            <text x={L + i * bw + bw / 2} y={H - 18} class="tick" text-anchor="middle">'{String(s.s).slice(2)}</text>
            {#if site.eras.length > 1}<text x={L + i * bw + bw / 2} y={H - 5} class="era" text-anchor="middle">{s.era === 'yahoo' ? 'Y' : 'S'}</text>{/if}
        {/each}
    </svg>
    <p class="keys">
        <span><i style="background:#f1c40f"></i>Champion</span>
        <span><i style="background:#8e44ad"></i>Lost the final</span>
        <span><i style="background:#2980b9"></i>Playoffs</span>
        <span><i style="background:#566573"></i>Missed</span>
        <span><i style="background:#27ae60"></i>{site.season}, in progress*</span>
        {#if site.eras.length > 1}<span>Y = Yahoo, S = Sleeper</span>{/if}
    </p>

    {#if h2h.length}
        <h3>Against everyone in the league now</h3>
        <p class="sub">Wins minus losses, regular season and real playoff games since {site.first_season}. Tap a name for the full rivalry.</p>
        <HBarChart items={h2h} format={(v) => (v > 0 ? `+${v}` : `${v}`)} ariaLabel="Head-to-head net wins for {nameOf(handle)}" />
    {/if}
</section>
{/if}

<style>
    .mh { max-width: 700px; margin: 1em auto 2em; padding: 0 1em; text-align: left; }
    h3 { margin: 1.4em 0 0.3em; }
    svg { width: 100%; height: auto; }
    .axis { stroke: currentColor; opacity: 0.3; }
    .tick, .lbl, .era { fill: currentColor; font-size: 11px; }
    .tick, .era { opacity: 0.7; }
    .lbl { font-weight: 600; }
    .keys { display: flex; flex-wrap: wrap; gap: 0.3em 1.2em; font-size: 0.85em; }
    .keys i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 0.35em; vertical-align: middle; }
    .sub { font-size: 0.85em; opacity: 0.75; margin: 0; }
</style>
