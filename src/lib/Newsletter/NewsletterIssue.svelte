<script>
    // The written newsletter for one week: masthead, lead story, a storyline
    // for every manager (carried from issue to issue), the week's moves,
    // rest-of-season outlooks, trends, history and links around the site.
    // Prose lives in src/lib/data/newsletter/<slug>.json, one file per issue,
    // never touched by the build. A week without a file shows nothing here.
    import { nameOf, managerLink, slugFor } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';
    import { onMount } from 'svelte';
    import { newsletters } from '$lib/utils/newsletters';

    export let nl;      // this issue's newsletter JSON
    export let recap;   // the recap for the same week (standings, scores)

    let ready = false;
    onMount(() => { ready = true; });

    const paras = (t) => String(t || '').split(/\n\s*\n/).filter(Boolean);
    const rec = (h) => (recap?.standings || []).find((s) => s.manager === h);
    const ord = (n) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
    const sosLabel = (o) => (o.sos_rest_rank === 1 ? 'Hardest schedule left'
        : o.sos_rest_rank === o.teams ? 'Easiest schedule left' : `${ord(o.sos_rest_rank)} hardest schedule left`);
    const moodLabel = { up: 'Rising', down: 'Sliding', flat: 'Holding' };

    // How many issues in a row this manager has carried the same storyline.
    const older = newsletters.filter((x) => x.slug < nl.slug).sort((a, b) => (a.slug < b.slug ? 1 : -1));
    function chapter(m) {
        let n = 1;
        for (const x of older) {
            const prev = (x.managers || []).find((y) => y.handle === m.handle);
            if (!prev || prev.arc !== m.arc) break;
            n += 1;
        }
        return n;
    }
    const lastArc = (m) => {
        const x = older[0];
        const prev = x && (x.managers || []).find((y) => y.handle === m.handle);
        return prev && prev.arc !== m.arc ? prev.arc : null;
    };
    let showAll = true;
    $: mine = ready ? $myTeam : null;
</script>

<article class="nl">
    <header class="mast">
        <div class="name">{nl.masthead}</div>
        {#if nl.tagline}<div class="tag">{nl.tagline}</div>{/if}
        <div class="issue">{recap?.season} season · Week {recap?.week}</div>
    </header>

    <h2 class="headline">{nl.headline}</h2>
    {#if nl.dek}<p class="dek">{nl.dek}</p>{/if}
    {#each paras(nl.lead) as p}<p class="lead">{p}</p>{/each}

    {#if nl.managers?.length}
        <section>
            <h3 class="sec">Around the league <small>every manager's story, in standings order</small></h3>
            {#if mine && nl.managers.some((m) => m.handle === mine)}
                <p class="jump"><a href="#nl-{mine}">Jump to your team ↓</a></p>
            {/if}
            <div class="cards">
                {#each nl.managers as m (m.handle)}
                    {@const s = rec(m.handle)}
                    {@const ch = chapter(m)}
                    {@const was = lastArc(m)}
                    <div class="card" id="nl-{m.handle}" class:mine={mine === m.handle}>
                        <div class="top">
                            <span class="who">{#if managerLink(m.handle)}<a href={managerLink(m.handle)}>{nameOf(m.handle)}</a>{:else}{nameOf(m.handle)}{/if}</span>
                            {#if m.record}<span class="rec" title={m.record_note || ''}>{m.record}</span>
                            {:else if s}<span class="rec">{s.w}-{s.l}{s.t ? `-${s.t}` : ''}</span>{/if}
                        </div>
                        <div class="arc">
                            <span class="mood {m.mood || 'flat'}">{moodLabel[m.mood] || 'Holding'}</span>
                            <b>{m.arc}</b>
                            {#if ch > 1}<small>chapter {ch}</small>{:else if was}<small>was: {was}</small>{/if}
                        </div>
                        {#each paras(m.text) as p}<p>{p}</p>{/each}
                        {#if m.outlook || m.odds}
                            <div class="outlook">
                                <span class="lbl">Rest of the way</span>
                                {#if m.odds}
                                    <div class="chips">
                                        <span><b>{m.odds.playoff}%</b> playoffs</span>
                                        <span><b>{m.odds.proj_w}</b> projected wins</span>
                                        <span><b>{m.odds.title}%</b> title</span>
                                        <span>{sosLabel(m.odds)}</span>
                                    </div>
                                {/if}
                                {#if m.outlook}<p>{m.outlook}</p>{/if}
                            </div>
                        {/if}
                        {#if m.next}
                            <p class="next">{m.next}
                                {#if m.next_opp}<a href="/rivalries/{slugFor(m.handle, m.next_opp)}">The rivalry →</a>{/if}
                            </p>
                        {/if}
                    </div>
                {/each}
            </div>
            <p class="more"><a href="/odds">How the odds are worked out →</a></p>
        </section>
    {/if}

    {#if nl.moves?.items?.length}
        <section>
            <h3 class="sec">Moves of the week</h3>
            {#if nl.moves.intro}<p class="sub">{nl.moves.intro}</p>{/if}
            {#each nl.moves.items as mv}
                <div class="move">
                    <div class="top">
                        <span class="kind {mv.kind}">{mv.kind}</span>
                        <b>{mv.title}</b>
                        <span class="mgrs">{(mv.managers || []).map(nameOf).join(' · ')}</span>
                    </div>
                    {#each paras(mv.text) as p}<p>{p}</p>{/each}
                    {#if mv.verdict}<p class="verdict">The call: {mv.verdict}</p>{/if}
                </div>
            {/each}
            <p class="more"><a href="/trade-grades">Every trade, graded →</a> <a href="/waivers">Waiver returns →</a> <a href="/transactions">All transactions →</a></p>
        </section>
    {/if}

    {#if nl.trends?.length || nl.history?.length}
        <div class="two">
            {#if nl.trends?.length}
                <section>
                    <h3 class="sec">Season trends</h3>
                    {#each nl.trends as t}<div class="note"><b>{t.title}</b><p>{t.text}</p></div>{/each}
                </section>
            {/if}
            {#if nl.history?.length}
                <section>
                    <h3 class="sec">From the history books</h3>
                    {#each nl.history as t}<div class="note"><b>{t.title}</b><p>{t.text}</p></div>{/each}
                    <p class="more"><a href="/record-book">The record book →</a></p>
                </section>
            {/if}
        </div>
    {/if}

    {#if nl.ahead}
        <section>
            <h3 class="sec">The week ahead</h3>
            {#each paras(nl.ahead) as p}<p>{p}</p>{/each}
            <p class="more"><a href="/preview">Full preview with win odds →</a></p>
        </section>
    {/if}

    {#if nl.links?.length}
        <section>
            <h3 class="sec">Around the site</h3>
            <div class="links">
                {#each nl.links as l}
                    <a class="lk" href={l.href}><b>{l.label} →</b><span>{l.why}</span></a>
                {/each}
            </div>
        </section>
    {/if}
</article>

<style>
    .nl { margin: 0.5em 0 2em; }
    .mast { text-align: center; border-top: 3px solid currentColor; border-bottom: 1px solid currentColor; padding: 0.6em 0 0.5em; margin-bottom: 1em; }
    .mast .name { font-family: Georgia, 'Times New Roman', serif; font-size: 2.1em; font-weight: 800; letter-spacing: 0.02em; line-height: 1.1; }
    .mast .tag { font-style: italic; opacity: 0.8; font-size: 0.9em; margin-top: 0.2em; }
    .mast .issue { text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.75em; opacity: 0.75; margin-top: 0.4em; }
    .headline { font-family: Georgia, 'Times New Roman', serif; font-size: 1.7em; line-height: 1.2; text-align: center; margin: 0.4em 0 0.2em; border: none; }
    .dek { text-align: center; font-size: 1.05em; opacity: 0.85; margin: 0 auto 1em; max-width: 680px; line-height: 1.5; }
    .lead { line-height: 1.65; font-size: 1.02em; }
    .lead:first-of-type::first-letter { font-family: Georgia, serif; float: left; font-size: 3.1em; line-height: 0.9; padding: 0.05em 0.1em 0 0; font-weight: 800; }
    section { margin-top: 1.6em; }
    h3.sec { font-size: 1.15em; border-bottom: 2px solid rgba(127,127,127,0.35); padding-bottom: 0.2em; margin: 0 0 0.6em; }
    h3.sec small { font-weight: 400; opacity: 0.65; font-size: 0.78em; margin-left: 0.4em; }
    .sub { opacity: 0.8; margin-top: 0; }
    .jump a, .more a, .next a { color: #3498db; }
    .more { margin: 0.5em 0 0; font-size: 0.9em; display: flex; gap: 1.2em; flex-wrap: wrap; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 0.8em; }
    .card { border: 1px solid rgba(127,127,127,0.35); border-radius: 10px; padding: 0.8em 0.9em; scroll-margin-top: 4em; }
    .card.mine { border-color: #27ae60; box-shadow: inset 4px 0 0 #27ae60; }
    .card p { margin: 0.45em 0 0; line-height: 1.55; font-size: 0.94em; }
    .top { display: flex; align-items: baseline; gap: 0.6em; flex-wrap: wrap; }
    .who { font-weight: 800; font-size: 1.08em; }
    .who a { color: inherit; }
    .rec { margin-left: auto; font-variant-numeric: tabular-nums; font-weight: 700; opacity: 0.85; }
    .arc { display: flex; align-items: center; gap: 0.5em; flex-wrap: wrap; margin-top: 0.3em; }
    .arc small { opacity: 0.65; font-style: italic; }
    .mood { font-size: 0.7em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; color: #fff; border-radius: 4px; padding: 0.15em 0.45em; }
    .mood.up { background: #1e8449; } .mood.down { background: #c0392b; } .mood.flat { background: #566573; }
    .outlook { margin-top: 0.6em; border-top: 1px dashed rgba(127,127,127,0.4); padding-top: 0.5em; }
    .outlook .lbl { font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; font-weight: 700; }
    .chips { display: flex; flex-wrap: wrap; gap: 0.35em; margin-top: 0.3em; }
    .chips span { font-size: 0.8em; border: 1px solid rgba(127,127,127,0.4); border-radius: 999px; padding: 0.12em 0.55em; }
    .next { font-size: 0.88em !important; opacity: 0.9; }
    .next a { margin-left: 0.3em; white-space: nowrap; }
    .move { border-left: 4px solid #2471a3; padding: 0.3em 0 0.3em 0.8em; margin: 0.8em 0; }
    .move p { margin: 0.35em 0 0; line-height: 1.55; }
    .kind { font-size: 0.7em; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; color: #fff; background: #2471a3; border-radius: 4px; padding: 0.15em 0.45em; }
    .kind.trade { background: #7d3c98; } .kind.swap { background: #ca6f1e; }
    .mgrs { opacity: 0.7; font-size: 0.88em; }
    .verdict { font-weight: 700; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2em; }
    @media (max-width: 640px) { .two { grid-template-columns: 1fr; } .cards { grid-template-columns: 1fr; } }
    .note { margin-bottom: 0.7em; }
    .note p { margin: 0.2em 0 0; line-height: 1.5; font-size: 0.94em; }
    .links { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 0.6em; }
    .lk { display: flex; flex-direction: column; gap: 0.25em; border: 1px solid rgba(127,127,127,0.35); border-radius: 8px; padding: 0.6em 0.75em; color: inherit; text-decoration: none; }
    .lk:hover { border-color: #3498db; }
    .lk b { color: #3498db; }
    .lk span { font-size: 0.86em; opacity: 0.8; line-height: 1.4; }
</style>
