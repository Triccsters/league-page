<script>
    // One row per team, one dot per week, plus a tick at the median.
    // rows: [{ label, values: [number], highlight? }]
    export let rows = [];
    export let ariaLabel = 'Strip chart';

    const ROW = 26, W = 640, LABEL_W = 130, PAD = 14;
    $: all = rows.flatMap(r => r.values);
    $: lo = all.length ? Math.floor(Math.min(...all) / 20) * 20 : 0;
    $: hi = all.length ? Math.ceil(Math.max(...all) / 20) * 20 : 100;
    $: x = (v) => LABEL_W + ((v - lo) / Math.max(1, hi - lo)) * (W - LABEL_W - PAD);
    $: ticks = Array.from({ length: Math.floor((hi - lo) / 20) + 1 }, (_, i) => lo + i * 20);
    $: H = rows.length * ROW + 28;
    const med = (v) => { const s = [...v].sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : 0; };
    const fit = (s) => (s.length > 17 ? s.slice(0, 16) + '…' : s);
</script>

<div class="wrap">
    <svg viewBox="0 0 {W} {H}" role="img" aria-label={ariaLabel}>
        {#each ticks as t}
            <line x1={x(t)} x2={x(t)} y1="0" y2={H - 22} class="grid" />
            <text x={x(t)} y={H - 6} class="tick" text-anchor="middle">{t}</text>
        {/each}
        {#each rows as r, i}
            <g transform="translate(0,{i * ROW})">
                {#if r.highlight}<rect x="0" y="1" width={W} height={ROW - 2} rx="4" class="hl" />{/if}
                <text x={LABEL_W - 8} y={ROW / 2 + 4} class="label" text-anchor="end"><title>{r.label}</title>{fit(r.label)}</text>
                {#each r.values as v}<circle cx={x(v)} cy={ROW / 2} r="4.5" class="dot"><title>{r.label}: {v}</title></circle>{/each}
                <line x1={x(med(r.values))} x2={x(med(r.values))} y1="5" y2={ROW - 5} class="med" />
            </g>
        {/each}
    </svg>
</div>

<style>
    .wrap { overflow-x: auto; }
    svg { width: 100%; min-width: 420px; height: auto; display: block; }
    .grid { stroke: rgba(127,127,127,0.2); }
    .tick { font-size: 11px; fill: currentColor; opacity: 0.6; }
    .label { font-size: 12px; fill: currentColor; }
    .dot { fill: #3498db; fill-opacity: 0.75; }
    .med { stroke: currentColor; stroke-width: 2; opacity: 0.8; }
    .hl { fill: rgba(39, 174, 96, 0.15); }
</style>