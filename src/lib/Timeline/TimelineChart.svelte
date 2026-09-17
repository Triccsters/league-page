<script>
    // Two-team running score, like Yahoo's "Matchup Timeline".
    export let slots = ['Wed', 'Thu', 'Sun early', 'Sun late', 'SNF', 'MNF'];
    export let a = { label: 'Team A', values: [] };   // drawn blue
    export let b = { label: 'Team B', values: [] };   // drawn red

    const W = 640, H = 260, L = 44, R = 16, T = 16, B = 34;

    $: max = Math.max(10, ...a.values, ...b.values);
    $: top = Math.ceil(max / 20) * 20;
    $: ticks = [0, 1, 2, 3, 4].map(i => Math.round((top / 4) * i));
    $: x = (i) => L + (i * (W - L - R)) / Math.max(1, slots.length - 1);
    $: y = (v) => T + (H - T - B) * (1 - v / top);
    $: path = (vals) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
</script>

<figure class="tl">
    <svg viewBox="0 0 {W} {H}" role="img" aria-label="Matchup timeline: {a.label} {a.values.at(-1)} vs {b.label} {b.values.at(-1)}">
        {#each ticks as t}
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} class="grid" />
            <text x={L - 6} y={y(t) + 4} class="tick" text-anchor="end">{t}</text>
        {/each}
        {#each slots as s, i}
            <text x={x(i)} y={H - 10} class="tick" text-anchor="middle">{s}</text>
        {/each}
        <path d={path(b.values)} class="line red" />
        <path d={path(a.values)} class="line blue" />
        {#each b.values as v, i}
            <circle cx={x(i)} cy={y(v)} r="4" class="dot red"><title>{b.label}: {v} after {slots[i]}</title></circle>
        {/each}
        {#each a.values as v, i}
            <circle cx={x(i)} cy={y(v)} r="4" class="dot blue"><title>{a.label}: {v} after {slots[i]}</title></circle>
        {/each}
    </svg>
    <figcaption>
        <span class="key"><i class="sw blue"></i>{a.label} <b>{a.values.at(-1) ?? 0}</b></span>
        <span class="key"><i class="sw red"></i>{b.label} <b>{b.values.at(-1) ?? 0}</b></span>
    </figcaption>
</figure>

<style>
    .tl { margin: 0.5em 0 1.2em; width: 100%; }
    svg { width: 100%; height: auto; display: block; }
    .grid { stroke: currentColor; opacity: 0.15; }
    .tick { fill: currentColor; opacity: 0.7; font-size: 12px; }
    .line { fill: none; stroke-width: 3; }
    .dot { stroke: #fff; stroke-width: 1.5; }
    .blue { stroke: #3498db; }
    .red { stroke: #e74c3c; }
    circle.blue { fill: #3498db; }
    circle.red { fill: #e74c3c; }
    figcaption { display: flex; justify-content: center; gap: 1.5em; flex-wrap: wrap; font-size: 0.95em; }
    .key { display: inline-flex; align-items: center; gap: 0.4em; }
    .sw { display: inline-block; width: 14px; height: 14px; border-radius: 50%; }
    .sw.blue { background: #3498db; }
    .sw.red { background: #e74c3c; }
</style>
