<script>
    // Career leaders: one card per category, the leader large and the next few listed under.
    // Layout from a league site T.J. shared 2026-11-13. Everything is counted from history.json games.
    import { onMount } from 'svelte';
    import { games, managers, nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });

    const BRACKET = new Set(['Quarterfinal', 'Semifinal', 'Championship']);
    const S = {};
    const get = (h) => (S[h] ||= { h, seasons: new Set(), w: 0, l: 0, t: 0, pf: 0, titles: 0, finals: 0, po: new Set(), pw: 0, pl: 0 });
    for (const g of games) {
        if (g.pa == null || g.pb == null || (!g.pa && !g.pb)) continue;
        for (const [me, mine, theirs] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
            if (!me || managers[me]?.hidden) continue;
            const s = get(me);
            s.seasons.add(g.season);
            if (!g.playoff) {
                s.pf += mine;
                if (mine > theirs) s.w++; else if (mine < theirs) s.l++; else s.t++;
            } else if (BRACKET.has(g.label)) {
                s.po.add(g.season);
                if (mine > theirs) s.pw++; else if (mine < theirs) s.pl++;
                if (g.label === 'Championship') { s.finals++; if (mine > theirs) s.titles++; }
            }
        }
    }
    const all = Object.values(S).map((s) => ({ ...s, n: s.seasons.size, g: s.w + s.l + s.t, pct: s.w + s.l + s.t ? (s.w + s.t / 2) / (s.w + s.l + s.t) : 0, apps: s.po.size }));
    const rec = (s) => `${s.w}-${s.l}${s.t ? `-${s.t}` : ''}`;
    const seas = (s) => `${s.n} season${s.n === 1 ? '' : 's'}`;
    const top = (list, key, n = 8) => [...list].filter((s) => s[key] > 0).sort((a, b) => b[key] - a[key] || b.pct - a.pct).slice(0, n);
    const minG = Math.min(20, Math.max(8, Math.round(Math.max(0, ...all.map((s) => s.g)) / 4)));
    const cards = [
        { t: 'Most championships', rows: top(all, 'titles'), v: (s) => s.titles, sub: seas },
        { t: 'Most title-game appearances', rows: top(all, 'finals'), v: (s) => s.finals, sub: seas },
        { t: 'Most playoff appearances', rows: top(all, 'apps'), v: (s) => s.apps, sub: seas },
        { t: 'Most playoff wins', q: 'bracket games only', rows: top(all, 'pw'), v: (s) => s.pw, sub: (s) => `${s.pw}-${s.pl}` },
        { t: 'Most regular-season wins', rows: top(all, 'w'), v: (s) => s.w, sub: rec },
        { t: 'Best winning percentage', q: `at least ${minG} games`, rows: top(all.filter((s) => s.g >= minG), 'pct'), v: (s) => `${(s.pct * 100).toFixed(1)}%`, sub: rec },
        { t: 'Most regular-season points', rows: top(all, 'pf'), v: (s) => s.pf.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }), sub: seas },
        { t: 'Most points per game', q: `at least ${minG} games`, rows: [...all].filter((s) => s.g >= minG).map((s) => ({ ...s, ppg: s.pf / s.g })).sort((a, b) => b.ppg - a.ppg).slice(0, 8), v: (s) => s.ppg.toFixed(2), sub: (s) => `${s.g} games` },
    ].filter((c) => c.rows.length);
</script>

{#if cards.length}
    <section class="cl">
        <p class="eyebrow">All time</p>
        <h2>Career Leaders</h2>
        <p class="sub">Counted from every game on record. Playoff numbers count bracket games, not consolation games.</p>
        <div class="grid">
            {#each cards as c}
                {@const lead = c.rows[0]}
                <section class="card">
                    <h3>{c.t}{#if c.q}<small>{c.q}</small>{/if}</h3>
                    <div class="lead" class:mine={ready && lead.h === $myTeam}>
                        <b>{c.v(lead)}</b>
                        <a href={managerLink(lead.h) || undefined}>{nameOf(lead.h)}</a>
                        <span>{c.sub(lead)}</span>
                    </div>
                    {#each c.rows.slice(1) as s, i}
                        <div class="row" class:mine={ready && s.h === $myTeam}>
                            <span class="n">{i + 2}</span>
                            <span class="who"><a href={managerLink(s.h) || undefined}>{nameOf(s.h)}</a><small>{c.sub(s)}</small></span>
                            <span class="v">{c.v(s)}</span>
                        </div>
                    {/each}
                </section>
            {/each}
        </div>
    </section>
{/if}

<style>
    .cl { max-width: 1100px; margin: 1.5em auto 2em; padding: 0 1em; text-align: left; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    h2 { margin: 0.1em 0 0.2em; text-transform: uppercase; font-style: italic; font-weight: 900; text-align: left; }
    .sub { opacity: 0.75; font-size: 0.9em; margin: 0 0 1em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.9em; }
    .card { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 16px; padding: 1.1em 1.1em 0.8em; }
    h3 { margin: 0 0 0.6em; font-size: 0.95em; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: #9fb0cc; display: flex; justify-content: space-between; gap: 0.8em; }
    h3 small { font-size: 0.7em; letter-spacing: 0.1em; opacity: 0.85; text-align: right; }
    .lead { border-left: 3px solid #ff7a2f; padding-left: 0.8em; margin-bottom: 0.7em; display: flex; flex-direction: column; }
    .lead b { font-size: 2em; line-height: 1.1; color: #fff; }
    .lead a, .who a { color: #6ea8ff; font-weight: 700; text-decoration: none; }
    .lead span { opacity: 0.75; font-size: 0.9em; }
    .row { display: grid; grid-template-columns: 1.6em 1fr auto; align-items: center; gap: 0.4em; padding: 0.4em 0; border-top: 1px solid #25304a; }
    .n { opacity: 0.6; font-weight: 700; }
    .who { display: flex; flex-direction: column; min-width: 0; }
    .who small { font-size: 0.7em; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.65; }
    .v { font-weight: 800; font-variant-numeric: tabular-nums; color: #fff; }
    .mine a { color: #7ee8b5; }
</style>
