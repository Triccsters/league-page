<script>
    // Power Lines: each team's place in the standings after every week, as crossing lines.
    // Look borrowed from 440andfriends.com (T.J., 2026-11-13). Rank = wins, then points for,
    // through that week, from the games in history.json. Avatars are the Sleeper ones in managers.json.
    import { onMount } from 'svelte';
    import { games, site, nameOf, currentManagers } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import managers from '$lib/data/managers.json';
    import * as leagueInfo from '$lib/utils/leagueInfo';

    let ready = false;
    onMount(() => { ready = true; });

    const COLORS = ['#4dd0e1', '#ff5d6c', '#ffd23f', '#7ee8b5', '#d67bff', '#ff9a3c', '#8fb3ff', '#b8e986', '#ff8fd0', '#c9d6df', '#5ec8a0', '#f4a261', '#9d8cff', '#e9c46a'];
    const pic = {};
    for (const m of managers || []) if (m.handle) pic[m.handle] = m.avatar || m.photo || null;

    const season = site.season;
    const reg = games.filter((g) => g.season === season && !g.playoff && g.pa != null && g.pb != null && (g.pa || g.pb));
    const weeks = [...new Set(reg.map((g) => g.week))].sort((a, b) => a - b);
    const teams = [...new Set([...(currentManagers || []), ...reg.flatMap((g) => [g.a, g.b])])].filter((h) => reg.some((g) => g.a === h || g.b === h));

    // rank[h][i] = place after weeks[i]
    const rank = {};
    const tot = {};
    for (const h of teams) { rank[h] = []; tot[h] = { w: 0, pf: 0 }; }
    for (const w of weeks) {
        for (const g of reg) {
            if (g.week !== w) continue;
            for (const [me, mine, theirs] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
                if (!tot[me]) continue;
                tot[me].pf += mine;
                tot[me].w += mine > theirs ? 1 : mine === theirs ? 0.5 : 0;
            }
        }
        const order = [...teams].sort((x, y) => tot[y].w - tot[x].w || tot[y].pf - tot[x].pf);
        order.forEach((h, i) => rank[h].push(i + 1));
    }
    const final = [...teams].sort((x, y) => rank[x][weeks.length - 1] - rank[y][weeks.length - 1]);
    const color = {};
    final.forEach((h, i) => { color[h] = COLORS[i % COLORS.length]; });

    const n = teams.length;
    const W = 900, L = 46, R = 58, T = 34, ROW = 44;
    const H = T + n * ROW + 10;
    const spots = +leagueInfo.playoffTeams || 0;
    let upto = weeks.length;      // slider
    let sel = null;               // traced team
    $: shownWeeks = weeks.slice(0, upto);
    const x = (i) => L + (weeks.length > 1 ? (i * (W - L - R)) / (weeks.length - 1) : 0);
    const y = (r) => T + (r - 1) * ROW + ROW / 2;
    const path = (h, k) => {
        let d = '';
        for (let i = 0; i < k; i++) {
            const px = x(i), py = y(rank[h][i]);
            if (!i) { d = `M${px},${py}`; continue; }
            const qx = x(i - 1), qy = y(rank[h][i - 1]), mx = (px + qx) / 2;
            d += ` C${mx},${qy} ${mx},${py} ${px},${py}`;
        }
        return d;
    };
    const dim = (h, s, mine) => (s ? (s === h ? 1 : 0.12) : 1);
    const pick = (h) => { sel = sel === h ? null : h; };
</script>

{#if weeks.length > 1 && n > 1}
    <section class="pl">
        <h2><span class="a">Power</span> Lines <small>the rise and fall, week to week</small></h2>
        <div class="box">
            <svg viewBox="0 0 {W} {H}" role="img" aria-label="Standings place by week">
                {#each weeks as w, i}
                    <line x1={x(i)} x2={x(i)} y1={T - 6} y2={H - 6} class="grid" />
                    <text x={x(i)} y={16} class="wk" class:now={i === upto - 1}>W{w}</text>
                {/each}
                {#each Array(n) as _, r}
                    <text x={14} y={y(r + 1) + 5} class="rk" class:in={spots && r < spots}>{r + 1}</text>
                {/each}
                {#if spots && spots < n}
                    <line x1={L - 20} x2={W - 8} y1={T + spots * ROW} y2={T + spots * ROW} class="cut" />
                    <text x={W - 10} y={T + spots * ROW - 5} class="cutlab">PLAYOFFS</text>
                {/if}
                {#each final as h (h)}
                    {@const k = shownWeeks.length}
                    {@const mine = ready && h === $myTeam}
                    <g opacity={dim(h, sel, mine)} on:click={() => pick(h)} on:keydown={(e) => e.key === 'Enter' && pick(h)} role="button" tabindex="0" aria-label={nameOf(h)} class="team">
                        <path d={path(h, k)} stroke={color[h]} stroke-width={mine || sel === h ? 5 : 3} fill="none" stroke-linecap="round" />
                        {#each shownWeeks as w, i}
                            <circle cx={x(i)} cy={y(rank[h][i])} r="4.5" fill="#cfd8dc" stroke={color[h]} stroke-width="2" />
                        {/each}
                        {#if k}
                            {@const ex = x(k - 1)}
                            {@const ey = y(rank[h][k - 1])}
                            <circle cx={ex} cy={ey} r="17" fill="#22272b" stroke={color[h]} stroke-width="4" />
                            {#if pic[h]}
                                <clipPath id="plc-{h}"><circle cx={ex} cy={ey} r="14.5" /></clipPath>
                                <image href={pic[h]} x={ex - 14.5} y={ey - 14.5} width="29" height="29" clip-path="url(#plc-{h})" preserveAspectRatio="xMidYMid slice" />
                            {:else}
                                <text x={ex} y={ey + 4} class="ini">{nameOf(h).slice(0, 2)}</text>
                            {/if}
                        {/if}
                    </g>
                {/each}
            </svg>
        </div>
        <div class="ctl">
            <input type="range" min="1" max={weeks.length} step="1" bind:value={upto} aria-label="Week" />
            <b>Week {weeks[upto - 1]}</b>
        </div>
        <div class="chips">
            {#each final as h}
                <button class:on={sel === h} class:mine={ready && h === $myTeam} style="--c:{color[h]}" on:click={() => pick(h)}>
                    {#if pic[h]}<img src={pic[h]} alt="" loading="lazy" />{/if}{nameOf(h)}
                </button>
            {/each}
        </div>
        <p class="note">Place in the standings after each week (wins, then points for). Drag the slider to rewind, or tap a name to trace one team.</p>
    </section>
{/if}

<style>
    .pl { max-width: 1000px; margin: 1.5em auto; padding: 1.2em 1em; background: #22272b; color: #eceff1; border-radius: 22px; }
    h2 { margin: 0 0 0.7em; font-size: 1.5em; text-transform: uppercase; letter-spacing: 0.03em; text-align: left; color: #fff; font-weight: 900; }
    .box { scrollbar-color: #5a6268 #2c3136; }
    h2 .a { color: #7ee8b5; font-size: 0.75em; }
    h2 small { float: right; font-size: 0.5em; font-weight: 400; opacity: 0.75; text-transform: none; letter-spacing: 0; margin-top: 0.9em; }
    .box { background: #33383d; border-radius: 12px; padding: 0.4em; overflow-x: auto; }
    svg { display: block; width: 100%; min-width: 560px; height: auto; }
    .grid { stroke: rgba(255,255,255,0.07); stroke-width: 1; }
    .wk { fill: #9aa5ab; font-size: 13px; font-weight: 800; text-anchor: middle; }
    .wk.now { fill: #fff; }
    .rk { fill: #9aa5ab; font-size: 17px; font-weight: 800; text-anchor: middle; }
    .rk.in { fill: #7ee8b5; }
    .cut { stroke: #7ee8b5; stroke-width: 2; }
    .cutlab { fill: #7ee8b5; font-size: 11px; font-weight: 800; text-anchor: end; }
    .ini { fill: #fff; font-size: 11px; font-weight: 800; text-anchor: middle; text-transform: uppercase; }
    .team { cursor: pointer; transition: opacity 0.2s; outline: none; }
    .ctl { display: flex; align-items: center; gap: 1em; margin: 0.9em 0.3em 0.6em; }
    .ctl input { flex: 1; accent-color: #1e8e6a; }
    .ctl b { text-transform: uppercase; white-space: nowrap; }
    .chips { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.45em; }
    .chips button { display: flex; align-items: center; gap: 0.5em; font: inherit; font-weight: 800; font-size: 0.85em; text-transform: uppercase; color: #cfd8dc; background: #2c3136; border: 2px solid transparent; border-radius: 999px; padding: 0.25em 0.7em 0.25em 0.3em; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-height: 2.2em; }
    .chips button.on { border-color: var(--c); color: #fff; }
    .chips button.mine { color: #7ee8b5; }
    .chips img { width: 1.7em; height: 1.7em; border-radius: 50%; border: 2px solid var(--c); object-fit: cover; flex: none; }
    .note { font-size: 0.85em; opacity: 0.7; margin: 0.8em 0.3em 0; text-align: left; }
</style>
