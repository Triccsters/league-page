<script>
    // Rivalry Hub: every head-to-head series between current managers scored 0 to 100.
    // Idea and weights from a league site T.J. shared 2026-11-13. Counted from history.json games.
    import { onMount } from 'svelte';
    import { games, site, nameOf, currentManagers, slugFor } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import managers from '$lib/data/managers.json';

    let ready = false;
    onMount(() => { ready = true; });
    const pic = {};
    for (const m of managers || []) if (m.handle) pic[m.handle] = m.avatar || m.photo || null;
    const BRACKET = new Set(['Quarterfinal', 'Semifinal', 'Championship']);
    const cur = new Set(currentManagers || []);

    const P = {};
    for (const g of games) {
        if (!cur.has(g.a) || !cur.has(g.b) || g.pa == null || g.pb == null || (!g.pa && !g.pb)) continue;
        const [x, y] = [g.a, g.b].sort();
        const p = (P[`${x}|${y}`] ||= { x, y, all: 0, n: 0, wx: 0, wy: 0, tie: 0, po: 0, title: 0, seasons: new Set(), last: 0, blow: null, close: null });
        p.all++;
        if (g.playoff && !BRACKET.has(g.label)) continue;          // consolation: counted as a meeting, not scored
        const px = g.a === x ? g.pa : g.pb, py = g.a === x ? g.pb : g.pa;
        p.n++; p.seasons.add(g.season); p.last = Math.max(p.last, g.season);
        if (px > py) p.wx++; else if (py > px) p.wy++; else p.tie++;
        if (g.playoff) { p.po++; if (g.label === 'Championship') p.title++; }
        const m = Math.abs(px - py), w = px >= py ? x : y;
        const rec = { m, w, hi: Math.max(px, py), lo: Math.min(px, py), season: g.season, week: g.week };
        if (!p.blow || m > p.blow.m) p.blow = rec;
        if (m > 0 && (!p.close || m < p.close.m)) p.close = rec;
    }
    const elig = Object.values(P).filter((p) => p.n >= 4 && p.seasons.size >= 2);
    const pr = (key) => {
        const vals = elig.map(key);
        return (v) => (elig.length > 1 ? (vals.filter((z) => z <= v).length - 1) / (elig.length - 1) : 1);
    };
    const fFreq = pr((p) => p.n), fPost = pr((p) => p.po + p.title), fLong = pr((p) => p.seasons.size);
    const list = elig.map((p) => {
        const comp = 1 - Math.abs(p.wx - p.wy) / p.n;
        const freq = fFreq(p.n), post = p.po ? fPost(p.po + p.title) : 0, rece = Math.max(0, 1 - 0.2 * (site.season - p.last)), lon = fLong(p.seasons.size);
        const parts = { comp: comp * 30, freq: freq * 25, post: post * 20, rece: rece * 15, lon: lon * 10 };
        return { ...p, comp, parts, score: Object.values(parts).reduce((a, b) => a + b, 0), lead: p.wx === p.wy ? null : p.wx > p.wy ? p.x : p.y, gap: Math.abs(p.wx - p.wy) };
    }).sort((a, b) => b.score - a.score);
    list.forEach((p, i) => { p.rank = i + 1; });

    const TABS = [
        ['comp', 'Most competitive', (l) => [...l].sort((a, b) => b.comp - a.comp || b.n - a.n)],
        ['played', 'Most played', (l) => [...l].sort((a, b) => b.n - a.n || b.score - a.score)],
        ['title', 'Championship rivalries', (l) => l.filter((p) => p.title).sort((a, b) => b.title - a.title || b.po - a.po)],
        ['lead', 'Biggest series leads', (l) => [...l].sort((a, b) => b.gap - a.gap || b.n - a.n)],
        ['recent', 'Recently active', (l) => [...l].sort((a, b) => b.last - a.last || b.score - a.score)],
    ].filter(([, , f]) => f(list).length);
    let tab = 'comp', showAll = false;
    $: focus = (TABS.find((t) => t[0] === tab) || TABS[0])?.[2](list).slice(0, 6) || [];
    const wins = (p, h) => (h === p.x ? p.wx : p.wy);
    const leadText = (p) => (p.lead ? `${nameOf(p.lead)} leads ${Math.max(p.wx, p.wy)}-${Math.min(p.wx, p.wy)}` : 'Series tied');
    const game = (r) => (r ? `${nameOf(r.w)} by ${r.m.toFixed(2)} (${r.hi.toFixed(2)} to ${r.lo.toFixed(2)}, ${r.season} wk ${r.week})` : 'none');
</script>

{#if list.length}
    <section class="rh">
        <p class="eyebrow">Top calculated rivalry</p>
        <h2>The league's biggest rivalry</h2>
        {#each [list[0], ...list.slice(1, showAll ? list.length : 7)] as p, i (p.x + p.y)}
            {#if i === 1}<p class="eyebrow gap">Calculated ranking</p><h2>Top rivalries <small>{list.length} ranked series</small></h2>{/if}
            <div class="slot" class:first={i === 0}>
                <article class="card" class:mine={ready && (p.x === $myTeam || p.y === $myTeam)}>
                    <header><span>#{p.rank}</span><b>{p.score.toFixed(1)}<small>/100</small></b></header>
                    <div class="vs">
                        {#each [p.x, p.y] as h, k}
                            {#if k}<em>vs</em>{/if}
                            <div class="side">{#if pic[h]}<img src={pic[h]} alt="" loading="lazy" />{/if}<strong>{nameOf(h)}</strong><b>{wins(p, h)}</b></div>
                        {/each}
                    </div>
                    <p class="lead">{leadText(p)}</p>
                    <div class="stats"><span><small>Meetings</small>{p.n}</span><span><small>Playoff</small>{p.po}</span><span><small>Title games</small>{p.title}</span><span><small>Last met</small>{p.last}</span></div>
                    <p class="g"><small>Biggest blowout</small>{game(p.blow)}</p>
                    <p class="g"><small>Closest game</small>{game(p.close)}</p>
                    <details><summary>Why this score</summary>
                        <p>How even {p.parts.comp.toFixed(1)} of 30 · how often {p.parts.freq.toFixed(1)} of 25 · playoffs {p.parts.post.toFixed(1)} of 20 · how recent {p.parts.rece.toFixed(1)} of 15 · how long {p.parts.lon.toFixed(1)} of 10{p.all > p.n ? `. ${p.all - p.n} consolation game${p.all - p.n === 1 ? '' : 's'} not counted` : ''}.</p>
                    </details>
                    <a class="btn" href="/rivalries/{slugFor(p.x, p.y)}">Head-to-head →</a>
                </article>
            </div>
        {/each}
        {#if list.length > 7}<button class="more" on:click={() => (showAll = !showAll)}>{showAll ? 'Show fewer' : `Show all ${list.length}`}</button>{/if}

        <p class="eyebrow gap">Rivalry explorer</p>
        <h2>Category focus</h2>
        <div class="tabs">{#each TABS as [k, label]}<button class:on={tab === k} on:click={() => (tab = k)}>{label}</button>{/each}</div>
        <div class="mini">
            {#each focus as p (p.x + p.y)}
                <a class="row" href="/rivalries/{slugFor(p.x, p.y)}" class:mine={ready && (p.x === $myTeam || p.y === $myTeam)}>
                    <span class="r">#{p.rank}</span><span class="nm">{nameOf(p.x)} <b>{p.wx}</b> to <b>{p.wy}</b> {nameOf(p.y)}</span><span class="m">{p.n} games{p.title ? ` · ${p.title} title` : ''} · {p.last}</span><span class="s">{p.score.toFixed(1)}</span>
                </a>
            {/each}
        </div>
        <details class="how"><summary>How rivalry scores work</summary>
            <p>Each series is scored 0 to 100: how close the win-loss record is to even (30), how often they have played (25), playoff meetings with title games counting double (20), how recently they met (15) and how many seasons they have met in (10). Frequency, playoffs and length are ranked against the other series, so scores move as history grows. A series needs at least 4 regular-season or playoff meetings across 2 seasons to be ranked. Consolation games are left out of the score. Current managers only.</p>
        </details>
    </section>
{/if}

<style>
    .rh { text-align: left; margin: 1em 0 2em; display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 0.9em; }
    .rh > * { grid-column: 1 / -1; }
    .rh > .slot:not(.first) { grid-column: auto; }
    .eyebrow { color: #ff7a2f; font-size: 0.72em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    .eyebrow.gap { margin-top: 1.2em; }
    h2 { margin: -0.6em 0 0; text-transform: uppercase; font-style: italic; font-weight: 900; border: 0; }
    h2 small { float: right; font-size: 0.5em; font-style: normal; font-weight: 400; opacity: 0.7; text-transform: none; margin-top: 0.8em; }
    .card { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 14px; padding: 0.9em 1em; height: 100%; box-sizing: border-box; }
    .first .card { border: 2px solid #ff7a2f; }
    .card.mine { box-shadow: inset 0 0 0 1px #2ecc71; }
    header { display: flex; justify-content: space-between; align-items: baseline; opacity: 0.9; }
    header span { font-style: italic; opacity: 0.7; } header b { font-size: 1.3em; } header small { font-size: 0.55em; opacity: 0.7; }
    .vs { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; text-align: center; margin: 0.4em 0; }
    .vs em { font-size: 0.75em; opacity: 0.6; font-style: normal; text-transform: uppercase; }
    .side { display: flex; flex-direction: column; align-items: center; gap: 0.15em; min-width: 0; }
    .side img { width: 2.6em; height: 2.6em; border-radius: 50%; object-fit: cover; }
    .first .side img { width: 3.6em; height: 3.6em; }
    .side strong { text-transform: uppercase; font-style: italic; font-size: 0.9em; overflow: hidden; text-overflow: ellipsis; max-width: 100%; white-space: nowrap; }
    .side b { font-size: 1.6em; line-height: 1; }
    .lead { text-align: center; color: #ff9a52; font-weight: 700; font-size: 0.88em; margin: 0.2em 0 0.6em; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); text-align: center; font-weight: 800; border-bottom: 1px solid #25304a; padding-bottom: 0.5em; margin-bottom: 0.5em; }
    small { display: block; font-size: 0.62em; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.65; }
    .g { margin: 0.25em 0; font-size: 0.82em; }
    details { font-size: 0.82em; margin: 0.4em 0 0.7em; } summary { cursor: pointer; color: #6ea8ff; } details p { opacity: 0.85; margin: 0.4em 0 0; line-height: 1.5; }
    .btn { display: inline-block; background: #1b2740; color: #e8edf5; text-decoration: none; font-size: 0.72em; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; border-radius: 8px; padding: 0.5em 0.9em; }
    .more { justify-self: start; font: inherit; color: #6ea8ff; background: none; border: 0; cursor: pointer; padding: 0; }
    .tabs { display: flex; flex-wrap: wrap; gap: 0.4em; }
    .tabs button { font: inherit; font-size: 0.75em; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: #cfd8e6; background: #131a2a; border: 1px solid #25304a; border-radius: 8px; padding: 0.5em 0.8em; cursor: pointer; }
    .tabs button.on { background: #1f3a6b; color: #fff; }
    .mini { display: grid; gap: 0.35em; }
    .row { display: grid; grid-template-columns: 2.6em 1fr auto 3em; gap: 0.6em; align-items: center; background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 10px; padding: 0.55em 0.8em; text-decoration: none; font-size: 0.9em; }
    .row.mine { border-color: #2ecc71; }
    .row .r { opacity: 0.6; font-style: italic; } .row .m { opacity: 0.7; font-size: 0.85em; white-space: nowrap; } .row .s { font-weight: 800; text-align: right; }
    .how { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 10px; padding: 0.7em 0.9em; }
    @media (max-width: 640px) { .row { grid-template-columns: 2.4em 1fr 3em; } .row .m { display: none; } }
</style>
