<script>
    // Horizontal bar chart. Handles negative values (drawn left of zero),
    // an optional reference line, and one highlighted row (the visitor's team).
    // items: [{ label, value, note?, highlight?, former?, color?, href? }]
    //   former: manager no longer in the league, drawn faded with a "(former)" tag
    // The label and value columns are sized from the text itself, so a long name
    // or a long note never runs into the bars or off the edge.
    export let items = [];
    export let refLine = null;        // { value, label }
    export let format = (v) => v;
    export let ariaLabel = 'Bar chart';

    import { afterUpdate } from 'svelte';

    const ROW = 26, W = 640;
    let CH = 7.1;                     // px per character; replaced by a real measurement once drawn
    const wide = (s) => String(s ?? '').length * CH;
    let svgEl;
    // The font is whatever the page uses, so guess first, then measure and settle.
    afterUpdate(() => {
        if (!svgEl) return;
        let widest = 0, chars = 0;
        for (const t of svgEl.querySelectorAll('text.label, text.val')) {
            const n = t.textContent.trim().length;
            if (!n) continue;
            let len = 0;
            try { len = t.getComputedTextLength(); } catch (e) { return; }
            if (len / n > widest) { widest = len / n; chars = n; }
        }
        if (widest && Math.abs(widest - CH) > 0.05) CH = widest;
    });
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

    const valueText = (i) => `${format(i.value)}${i.note ? ` · ${i.note}` : ''}`;
    const labelText = (i) => `${i.label}${i.former ? ' (former)' : ''}`;
    // columns, sized from the longest text in each
    $: LABEL_W = clamp(Math.max(0, ...items.map(i => wide(labelText(i)))) + 12, 70, 210);
    $: VALUE_W = clamp(Math.max(0, ...items.map(i => wide(valueText(i)))) + 12, 52, 230);
    $: plotW = Math.max(120, W - LABEL_W - VALUE_W);
    // a label too long for its column is cut with an ellipsis; the full text stays in the tooltip
    $: fit = (s) => {
        const max = Math.floor((LABEL_W - 12) / CH);
        return s.length > max ? s.slice(0, Math.max(1, max - 1)).trimEnd() + '…' : s;
    };

    $: min = Math.min(0, ...items.map(i => i.value), refLine ? refLine.value : 0);
    $: max = Math.max(0, ...items.map(i => i.value), refLine ? refLine.value : 0) || 1;
    $: span = max - min || 1;
    $: x = (v) => LABEL_W + ((v - min) / span) * plotW;
    $: H = items.length * ROW + (refLine ? 18 : 6);
    $: top = refLine ? 16 : 2;
    const colorFor = (i) => i.color || (i.highlight ? '#27ae60' : i.value < 0 ? '#e74c3c' : '#3498db');
    // the value sits outside the bar unless that would hit the labels or the edge
    $: placeValue = (i) => {
        const w = wide(valueText(i));
        if (i.value < 0) {
            const outside = x(i.value) - 4;
            return outside - w < LABEL_W + 2
                ? { x: x(i.value) + 4, anchor: 'start', inside: true }
                : { x: outside, anchor: 'end', inside: false };
        }
        const outside = x(i.value) + 4;
        return outside + w > W - 2
            ? { x: x(i.value) - 4, anchor: 'end', inside: true }
            : { x: outside, anchor: 'start', inside: false };
    };
</script>

<svg bind:this={svgEl} viewBox="0 0 {W} {H}" role="img" aria-label={ariaLabel}>
    {#if min < 0}
        <line x1={x(0)} x2={x(0)} y1={top - 2} y2={H} class="zero" />
    {/if}
    {#each items as it, i}
        {@const y = top + i * ROW}
        {@const v = placeValue(it)}
        <g class:hl={it.highlight} class:former={it.former}>
            <title>{labelText(it)}: {format(it.value)}{it.note ? ` (${it.note})` : ''}</title>
            <text x={LABEL_W - 8} y={y + ROW / 2 + 4} text-anchor="end" class="label">{#if it.href}<a href={it.href}>{fit(labelText(it))}</a>{:else}{fit(labelText(it))}{/if}</text>
            <rect x={Math.min(x(0), x(it.value))} y={y + 4} height={ROW - 8}
                width={Math.max(1, Math.abs(x(it.value) - x(0)))} rx="3" fill={colorFor(it)} />
            <text x={v.x} y={y + ROW / 2 + 4} text-anchor={v.anchor} class="val" class:inside={v.inside}>{valueText(it)}</text>
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
    .val.inside { fill: #fff; opacity: 0.95; font-weight: 600; paint-order: stroke; stroke: rgba(0,0,0,0.35); stroke-width: 2px; }
    .hl .label { font-weight: 700; fill: #27ae60; }
    .former rect { opacity: 0.45; }
    .former .label { opacity: 0.6; font-style: italic; }
    .zero { stroke: currentColor; opacity: 0.35; }
    .ref { stroke: #f39c12; stroke-width: 2; stroke-dasharray: 5 4; }
    .reftxt { fill: #f39c12; font-size: 11px; font-weight: 600; }
</style>
