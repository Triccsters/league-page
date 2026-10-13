<script>
    // Points for (across) against points against (up), one dot per team.
    // The dashed lines are the league averages, so each corner reads as a kind of season.
    // points: [{ label, x, y, highlight? }]
    export let points = [];
    export let ariaLabel = 'Points for against points against';

    const W = 640, H = 420, L = 54, R = 16, T = 16, B = 44;
    const nice = (v, up) => (up ? Math.ceil(v / 50) * 50 : Math.floor(v / 50) * 50);
    $: xs = points.map(p => p.x);
    $: ys = points.map(p => p.y);
    $: x0 = nice(Math.min(...xs, ...ys) - 10, false);
    $: x1 = nice(Math.max(...xs, ...ys) + 10, true);
    $: sx = (v) => L + ((v - x0) / Math.max(1, x1 - x0)) * (W - L - R);
    $: sy = (v) => H - B - ((v - x0) / Math.max(1, x1 - x0)) * (H - T - B);
    $: ax = xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
    $: ay = ys.reduce((a, b) => a + b, 0) / Math.max(1, ys.length);
    $: ticks = Array.from({ length: Math.floor((x1 - x0) / 50) + 1 }, (_, i) => x0 + i * 50);
    const short = (s) => (s.length > 12 ? s.slice(0, 11) + '…' : s);
</script>

{#if points.length}
<div class="wrap">
    <svg viewBox="0 0 {W} {H}" role="img" aria-label={ariaLabel}>
        {#each ticks as t}
            <line x1={sx(t)} x2={sx(t)} y1={T} y2={H - B} class="grid" />
            <line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} class="grid" />
            <text x={sx(t)} y={H - B + 16} class="tick" text-anchor="middle">{t}</text>
            <text x={L - 6} y={sy(t) + 4} class="tick" text-anchor="end">{t}</text>
        {/each}
        <line x1={sx(ax)} x2={sx(ax)} y1={T} y2={H - B} class="avg" />
        <line x1={L} x2={W - R} y1={sy(ay)} y2={sy(ay)} class="avg" />
        <text x={W - R - 4} y={T + 12} class="corner" text-anchor="end">Scored a lot, faced a lot</text>
        <text x={W - R - 4} y={H - B - 6} class="corner" text-anchor="end">Scored a lot, easy schedule</text>
        <text x={L + 4} y={T + 12} class="corner">Scored little, faced a lot</text>
        <text x={L + 4} y={H - B - 6} class="corner">Scored little, easy schedule</text>
        {#each points as p}
            <g class:hl={p.highlight}>
                <circle cx={sx(p.x)} cy={sy(p.y)} r={p.highlight ? 7 : 5.5} class="dot"><title>{p.label}: {p.x} for, {p.y} against</title></circle>
                <text x={sx(p.x) + 8} y={sy(p.y) + 4} class="name">{short(p.label)}</text>
            </g>
        {/each}
        <text x={(L + W - R) / 2} y={H - 6} class="axis" text-anchor="middle">Points for</text>
        <text x="14" y={(T + H - B) / 2} class="axis" text-anchor="middle" transform="rotate(-90 14 {(T + H - B) / 2})">Points against</text>
    </svg>
</div>
{/if}

<style>
    .wrap { overflow-x: auto; margin: 0.8em 0; }
    svg { width: 100%; min-width: 420px; height: auto; display: block; }
    .grid { stroke: rgba(127,127,127,0.18); }
    .avg { stroke: currentColor; stroke-dasharray: 4 4; opacity: 0.45; }
    .tick { font-size: 11px; fill: currentColor; opacity: 0.6; }
    .axis { font-size: 12px; fill: currentColor; opacity: 0.8; }
    .corner { font-size: 11px; fill: currentColor; opacity: 0.5; font-style: italic; }
    .dot { fill: #3498db; fill-opacity: 0.85; }
    .name { font-size: 11px; fill: currentColor; }
    .hl .dot { fill: #27ae60; }
    .hl .name { font-weight: 700; }
</style>