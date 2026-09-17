<script>
    // Horizontal bar chart. Handles negative values (drawn left of zero),
    // an optional reference line, and one highlighted row (the visitor's team).
    // items: [{ label, value, note?, highlight?, former?, color?, href? }]
    //   former: manager no longer in the league, drawn faded with a "(former)" tag
    export let items = [];
    export let refLine = null;        // { value, label }
    export let format = (v) => v;
    export let ariaLabel = 'Bar chart';

    const ROW = 26, LABEL_W = 150, VALUE_W = 64, W = 640;

    $: min = Math.min(0, ...items.map(i => i.value), refLine ? refLine.value : 0);
    $: max = Math.max(0, ...items.map(i => i.value), refLine ? refLine.value : 0) || 1;
    $: span = max - min || 1;
    $: plotW = W - LABEL_W - VALUE_W;
    $: x = (v) => LABEL_W + ((v - min) / span) * plotW;
    $: H = items.length * ROW + (refLine ? 18 : 6);
    $: top = refLine ? 16 : 2;
    const colorFor = (i) => i.color || (i.highlight ? '#27ae60' : i.value < 0 ? '#e74c3c' : '#3498db');
</script>

<svg viewBox="0 0 {W} {H}" role="img" aria-label={ariaLabel}>
    {#if min < 0}
        <line x1={x(0)} x2={x(0)} y1={top - 2} y2={H} class="zero" />
    {/if}
    {#each items as it, i}
        {@const y = top + i * ROW}
        <g class:hl={it.highlight} class:former={it.former}>
            <text x={LABEL_W - 8} y={y + ROW / 2 + 4} text-anchor="end" class="label">
                {#if it.href}<a href={it.href}>{it.label}</a>{:else}{it.label}{/if}{#if it.former}<tspan class="ftag"> (former)</tspan>{/if}
            </text>
            <rect x={Math.min(x(0), x(it.value))} y={y + 4} height={ROW - 8}
                width={Math.max(1, Math.abs(x(it.value) - x(0)))} rx="3" fill={colorFor(it)}>
                <title>{it.label}{it.former ? ' (no longer in the league)' : ''}: {format(it.value)}{it.note ? ` (${it.note})` : ''}</title>
            </rect>
            <text x={it.value < 0 ? x(it.value) - 4 : x(it.value) + 4} y={y + ROW / 2 + 4}
                text-anchor={it.value < 0 ? 'end' : 'start'} class="val">{format(it.value)}{it.note ? ` · ${it.note}` : ''}</text>
        </g>
    {/each}
    {#if refLine}
        <line x1={x(refLine.value)} x2={x(refLine.value)} y1={top - 4} y2={H} class="ref" />
        <text x={x(refLine.value)} y={11} text-anchor="middle" class="reftxt">{refLine.label}</text>
    {/if}
</svg>

<style>
    svg { width: 100%; height: auto; display: block; margin: 0.5em 0 1em; }
    .label, .val { fill: currentColor; font-size: 12px; }
    .label a { fill: #3498db; }
    .val { opacity: 0.8; }
    .hl .label { font-weight: 700; fill: #27ae60; }
    .former rect { opacity: 0.45; }
    .former .label { opacity: 0.6; font-style: italic; }
    .ftag { font-size: 10px; }
    .zero { stroke: currentColor; opacity: 0.35; }
    .ref { stroke: #f39c12; stroke-width: 2; stroke-dasharray: 5 4; }
    .reftxt { fill: #f39c12; font-size: 11px; font-weight: 600; }
</style>
