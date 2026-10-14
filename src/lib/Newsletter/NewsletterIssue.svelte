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
    // tracker cells written "@@handle" are teams
    const isTeam = (c) => typeof c === 'string' && c.startsWith('@@');
    const th = (c) => c.slice(2);
    const fmtDate = (d) => { const [y, m, dd] = String(d || '').split('-'); return m ? `${+m}/${+dd}` : ''; };
    const byOwner = (rows) => {
        const g = {};
        for (const r of rows || []) (g[r.h] = g[r.h] || []).push(r.n);
        return Object.entries(g);
    };
    const pmove = (t) => (t.prev ? t.prev - t.rank : 0);
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

    {#if nl.take?.text || nl.take?.shoutouts?.length}
        <section class="take">
            <h3 class="sec">{nl.take.byline || "T.J.'s take"}</h3>
            {#each paras(nl.take.text) as p}<p>{p}</p>{/each}
            {#if nl.take.shoutouts?.length}
                <div class="lbl">Shout-outs and roasts</div>
                <ul>{#each nl.take.shoutouts as x}<li>{x}</li>{/each}</ul>
            {/if}
        </section>
    {/if}

    {#if nl.power?.teams?.length}
        <section>
            <h3 class="sec">Power rankings <small>after week {nl.power.through_week}</small></h3>
            <ol class="pw">
                {#each nl.power.teams as t (t.h)}
                    {@const mv = pmove(t)}
                    <li class:mine={mine === t.h}>
                        <span class="rk">{t.rank}</span>
                        <span class="mv" class:up={mv > 0} class:down={mv < 0}>{mv > 0 ? `▲${mv}` : mv < 0 ? `▼${-mv}` : '·'}</span>
                        <a class="nm" href="#nl-{t.h}">{nameOf(t.h)}</a>
                        <span class="pp">ROS {ord(t.ros_rank)}{#if t.dyn_rank} · Dyn {ord(t.dyn_rank)}{/if}</span>
                    </li>
                {/each}
            </ol>
            <p class="more"><a href="/">How they are ranked, on the home page →</a></p>
        </section>
    {/if}

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
                        {#if m.tags?.length}
                            <div class="tags">{#each m.tags as t}<span class="t {t.k}">{t.t}</span>{/each}</div>
                        {/if}
                        {#each paras(m.text) as p}<p>{p}</p>{/each}
                        {#if m.tj_note}<p class="tjn"><b>{nl.take?.byline || "T.J.'s take"}:</b> {m.tj_note}</p>{/if}
                        {#if m.nfl_hits?.length && nl.nfl?.items}
                            <div class="hits"><span class="lbl">In the NFL news</span>
                                {#each m.nfl_hits as i}{@const x = nl.nfl.items[i]}{#if x}<a href="#nfl-{i}">{x.headline}</a>{/if}{/each}
                            </div>
                        {/if}
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

    {#if nl.nfl?.items?.length}
        <section>
            <h3 class="sec">Around the NFL <small>the real week, and who it hits here</small></h3>
            {#if nl.nfl.intro}{#each paras(nl.nfl.intro) as p}<p class="sub">{p}</p>{/each}{/if}
            {#each nl.nfl.items as x, i}
                <div class="nfl" id="nfl-{i}">
                    <div class="top">
                        <span class="kind {x.kind}">{x.kind === 'news' ? 'News' : 'Story'}</span>
                        <a class="hl" href={x.url} target="_blank" rel="noopener">{x.headline}</a>
                        <span class="dt">{fmtDate(x.date)}{#if x.teams?.length} · {x.teams.join(', ')}{/if}</span>
                    </div>
                    {#if x.note}{#each paras(x.note) as p}<p>{p}</p>{/each}{/if}
                    {#if x.named?.length}
                        <p class="own"><b>Owned here:</b>
                            {#each byOwner(x.named) as [h, ns], j}{j ? ' · ' : ''}{ns.join(', ')} (<a href="#nl-{h}">{nameOf(h)}</a>){/each}
                        </p>
                    {/if}
                    {#if x.ripple?.length}
                        <p class="own rip"><b>Same offense:</b>
                            {#each byOwner(x.ripple.slice(0, 10)) as [h, ns], j}{j ? ' · ' : ''}{ns.join(', ')} (<a href="#nl-{h}">{nameOf(h)}</a>){/each}{#if x.ripple.length > 10} · and {x.ripple.length - 10} more{/if}
                        </p>
                    {/if}
                </div>
            {/each}
            <p class="fine">Headlines and links from ESPN, read {String(nl.nfl.read_at || '').slice(0, 10)}. {nl.nfl.note}</p>
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
            {#if nl.take?.moves}<div class="tjbox"><b>{nl.take.byline || "T.J.'s take"}</b>{#each paras(nl.take.moves) as p}<p>{p}</p>{/each}</div>{/if}
            <p class="more"><a href="/trade-grades">Every trade, graded →</a> <a href="/waivers">Waiver returns →</a> <a href="/transactions">All transactions →</a></p>
        </section>
    {/if}

    {#each [['review', 'The races', 'who is winning the awards nobody hands out until December'], ['ahead', 'Looking ahead', 'odds, byes and the trade market']] as [key, title, sub]}
        {#if nl.board?.[key]?.length}
            <section>
                <h3 class="sec">{title} <small>{sub}</small></h3>
                <div class="board">
                    {#each nl.board[key] as c (c.id)}
                        <div class="bc">
                            <a class="bt" href="/trackers#{c.id}">{c.title} →</a>
                            <table>
                                <thead><tr>{#each c.cols as col}<th>{col}</th>{/each}</tr></thead>
                                <tbody>
                                    {#each c.rows as row}
                                        <tr class:mine={mine && row.some((x) => isTeam(x) && th(x) === mine)}>
                                            {#each row as cell}<td>{#if isTeam(cell)}<a href="#nl-{th(cell)}">{nameOf(th(cell))}</a>{:else}{cell}{/if}</td>{/each}
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/each}
                </div>
                <p class="more"><a href="/trackers">Every tracker, full tables →</a></p>
            </section>
        {/if}
    {/each}

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
            {#if nl.take?.picks?.length}
                <div class="tjbox"><b>{nl.take.byline || "T.J.'s take"}: my picks</b>
                    <table class="picks"><tbody>{#each nl.take.picks as k}<tr><td>{k.matchup}</td><td><b>{k.pick}</b></td><td>{k.why || ''}</td></tr>{/each}</tbody></table>
                </div>
            {/if}
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
    .pw { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 0.3em 1em; }
    .pw li { display: grid; grid-template-columns: 1.6em 2.2em 1fr auto; align-items: center; gap: 0.4em; padding: 0.2em 0.3em; border-bottom: 1px solid rgba(127,127,127,0.18); }
    .pw li.mine { background: rgba(39,174,96,0.14); }
    .pw .rk { font-weight: 800; text-align: center; }
    .pw .mv { font-size: 0.75em; font-weight: 700; opacity: 0.7; }
    .pw .mv.up { color: #2ecc71; opacity: 1; } .pw .mv.down { color: #e74c3c; opacity: 1; }
    .pw .nm { color: inherit; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pw .pp { font-size: 0.75em; opacity: 0.75; white-space: nowrap; }
    .tags { display: flex; flex-wrap: wrap; gap: 0.3em; margin-top: 0.4em; }
    .tags .t { font-size: 0.72em; font-weight: 700; border-radius: 999px; padding: 0.1em 0.55em; border: 1px solid rgba(127,127,127,0.5); }
    .tags .t.power { border-color: #27ae60; } .tags .t.dyn { border-color: #8e44ad; } .tags .t.lead { border-color: #e67e22; }
    .hits { margin-top: 0.5em; display: flex; flex-direction: column; gap: 0.15em; font-size: 0.85em; }
    .hits .lbl, .outlook .lbl { font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; font-weight: 700; }
    .hits a { color: #3498db; }
    .nfl { border-left: 4px solid #c0392b; padding: 0.3em 0 0.3em 0.8em; margin: 0.8em 0; }
    .nfl .hl { color: inherit; font-weight: 700; }
    .nfl .dt { opacity: 0.65; font-size: 0.82em; white-space: nowrap; }
    .nfl p { margin: 0.3em 0 0; line-height: 1.5; font-size: 0.92em; }
    .nfl .own a { color: #3498db; }
    .nfl .rip { opacity: 0.8; }
    .kind.news { background: #c0392b; } .kind.story { background: #566573; }
    .fine { font-size: 0.78em; opacity: 0.65; margin-top: 0.6em; }
    .board { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); gap: 0.8em; }
    .bc { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.55em 0.65em; min-width: 0; overflow-x: auto; }
    .bt { display: block; font-weight: 800; color: #3498db; margin-bottom: 0.3em; }
    .bc table { width: 100%; border-collapse: collapse; font-size: 0.82em; }
    .bc th { text-align: left; font-size: 0.78em; text-transform: uppercase; opacity: 0.65; padding: 0.15em 0.3em; white-space: nowrap; }
    .bc td { padding: 0.2em 0.3em; border-top: 1px solid rgba(127,127,127,0.15); }
    .bc td a { color: inherit; font-weight: 600; }
    .bc tr.mine td { background: rgba(39,174,96,0.14); }
    .take { border: 2px solid #27ae60; border-radius: 10px; padding: 0.6em 1em 0.8em; }
    .take h3.sec { border-bottom: none; color: #27ae60; }
    .take p { line-height: 1.6; }
    .take .lbl { font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; font-weight: 700; margin-top: 0.6em; }
    .tjn { border-left: 3px solid #27ae60; padding-left: 0.6em; }
    .tjbox { border-left: 4px solid #27ae60; padding: 0.3em 0 0.3em 0.8em; margin: 0.8em 0; }
    .tjbox p { margin: 0.3em 0 0; line-height: 1.55; }
    .picks { border-collapse: collapse; margin-top: 0.4em; font-size: 0.9em; }
    .picks td { padding: 0.2em 0.6em 0.2em 0; border-top: 1px solid rgba(127,127,127,0.2); }
</style>
