<script>
    // Best-ever lineup: the players who scored the most for this manager, fitted
    // into the league's own starting lineup (T.J., 2026-11-13).
    import { onMount } from 'svelte';
    import rules from '$lib/data/rules.json';
    import { playerImg, hideBroken } from '$lib/utils/avatars';
    export let handle;

    let players = null;
    onMount(async () => {
        try { players = await fetch('/data/players.json').then(r => r.json()); } catch (e) { players = null; }
    });

    const NAMED = { QB: ['QB'], RB: ['RB'], WR: ['WR'], TE: ['TE'], Kicker: ['K'], K: ['K'], 'Team defense': ['DEF'], DEF: ['DEF'] };
    const SHORT = { Kicker: 'K', 'Team defense': 'DEF' };
    // "Flex (RB/WR/TE)" names its own positions; bench, IR and taxi spots are not lineup slots
    const slots = (rules.lineup || []).flatMap(({ name, count }) => {
        const inside = /\(([^)]+)\)/.exec(name);
        const elig = NAMED[name] || (inside ? inside[1].split('/').map(s => s.trim()) : null);
        if (!elig) return [];
        const label = SHORT[name] || name.replace(/\s*\(.*\)/, '');
        return Array.from({ length: count }, () => ({ label, elig }));
    });
    const r1 = (x) => Math.round(x * 10) / 10;

    $: mine = !players ? [] : players.players.map(p => {
        const s = p.s.filter(x => x[1] === handle && x[3] > 0);
        if (!s.length) return null;
        const yrs = s.map(x => x[0]);
        return { k: p.k, n: p.n, pos: p.p, id: p.id, pts: s.reduce((t, x) => t + x[2], 0), st: s.reduce((t, x) => t + x[3], 0),
                 from: Math.min(...yrs), to: Math.max(...yrs) };
    }).filter(Boolean).sort((a, b) => b.pts - a.pts);
    // tightest slots pick first, so a flex spot never takes the only quarterback
    $: lineup = (() => {
        const used = new Set(), out = new Array(slots.length).fill(null);
        slots.map((s, i) => ({ ...s, i })).sort((a, b) => a.elig.length - b.elig.length).forEach(s => {
            const p = mine.find(x => !used.has(x.k) && s.elig.includes(x.pos));
            if (p) { used.add(p.k); out[s.i] = p; }
        });
        return out;
    })();
    $: total = lineup.reduce((t, p) => t + (p ? p.pts : 0), 0);
</script>

{#if players && slots.length && lineup.some(Boolean)}
    <section class="bl">
        <p class="eyebrow">Best-ever lineup</p>
        <h3>The all-time starting {slots.length}</h3>
        <p class="sub">The players who scored the most for this team while in a lineup, fitted into the league's starting spots. {r1(total).toLocaleString('en-US')} points between them.</p>
        <div class="grid">
            {#each slots as s, i}
                <div class="cell">
                    <span class="spot">{s.label}</span>
                    {#if lineup[i]}
                        <span class="pic">{#if playerImg(lineup[i])}<img class:logo={lineup[i].pos === 'DEF'} src={playerImg(lineup[i])} alt="" loading="lazy" on:error={hideBroken} />{/if}</span>
                        <span class="txt"><b>{lineup[i].n}</b><small>{lineup[i].st} starts, {lineup[i].from === lineup[i].to ? lineup[i].from : `${lineup[i].from} to ${lineup[i].to}`}</small></span>
                        <span class="v">{r1(lineup[i].pts).toLocaleString('en-US')}</span>
                    {:else}
                        <span class="pic"></span><span class="txt"><small>Nobody yet</small></span><span class="v"></span>
                    {/if}
                </div>
            {/each}
        </div>
    </section>
{/if}

<style>
    .bl { max-width: 900px; margin: 0.5em auto 2em; padding: 0 1em; text-align: left; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    h3 { margin: 0.1em 0; font-size: 1.15em; }
    .sub { opacity: 0.72; font-size: 0.84em; margin: 0 0 0.7em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 0.5em; }
    .cell { display: grid; grid-template-columns: 3.4em 36px 1fr auto; gap: 0.55em; align-items: center; background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 12px; padding: 0.5em 0.7em; min-width: 0; }
    .spot { font-size: 0.68em; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: #ff9a5c; }
    .pic { width: 36px; height: 36px; border-radius: 50%; overflow: hidden; background: #0b101c; display: inline-block; }
    .pic img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .pic img.logo { object-fit: contain; }
    .txt { min-width: 0; display: flex; flex-direction: column; }
    .txt b { color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .txt small { color: #9fb0cc; font-size: 0.76em; }
    .v { font-weight: 800; color: #fff; font-variant-numeric: tabular-nums; }
</style>
