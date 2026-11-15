<script>
    // Record Watch: records within reach this season, records already broken, and
    // career milestones. Everything comes from src/lib/data/record_watch.json, which
    // scripts/record_watch.py rebuilds at every update from history.json.
    //   mode="book"     the full block at the top of the Record Book
    //   mode="home"     a short strip on the home page, only when something is live
    //   mode="news"     the box inside a newsletter issue (the lines as they stood that week)
    //   mode="manager"  one manager's card (pass handle)
    import rw from '$lib/data/record_watch.json';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { avatarOf, hideBroken } from '$lib/utils/avatars';

    export let mode = 'book';
    export let handle = null;
    export let slug = null;

    // "{handle} did a thing" -> pieces, so names can be links
    const parts = (text) => String(text || '').split(/(\{[^}]+\})/).filter(Boolean)
        .map((p) => (p[0] === '{' ? { h: p.slice(1, -1) } : { t: p }));
    const n = (x) => Number(x).toLocaleString('en-US', { maximumFractionDigits: 2 });
    const TAG = { broken: 'Record broken', fresh: 'Set this season', milestone: 'Milestone', pass: 'All-time list', chase: 'Within reach', streak: 'Streak' };

    const lines = rw?.lines || [];
    const live = (rw?.records || []).filter((r) => r.status !== 'safe');
    const season = live.filter((r) => r.group === 'season');
    const streaks = live.filter((r) => r.group === 'streak');
    const fresh = rw?.fresh || [];
    const reached = (rw?.milestones || []).filter((m) => m.reached);
    const coming = (rw?.milestones || []).filter((m) => !m.reached);
    const passing = rw?.passing || [];
    const left = rw?.weeks_left ?? 0;
    const sub = rw?.through_week ? `Through week ${rw.through_week}. ${left ? `${left} regular-season week${left === 1 ? '' : 's'} left.` : 'The regular season is over.'}` : '';

    $: homeLines = lines.filter((l) => l.k !== 'chase' || lines.length < 4).slice(0, 3);
    $: newsLines = (slug && rw?.snap?.[slug]) || [];
    $: mine = handle ? lines.filter((l) => l.h === handle || l.holder === handle) : [];
    $: myWins = handle ? (rw?.milestones || []).find((m) => m.h === handle && m.detail) : null;
    let open = {};
</script>

{#snippet say(text)}{#each parts(text) as p}{#if p.h}{#if managerLink(p.h)}<a class="nm" href={managerLink(p.h)}>{nameOf(p.h)}</a>{:else}<b class="nm">{nameOf(p.h)}</b>{/if}{:else}{p.t}{/if}{/each}{/snippet}

{#snippet detail(m)}
    {@const d = m.detail}
    <div class="detail">
        <p><b>Wins by season</b></p>
        <div class="bys">{#each d.by_season as [s, w]}<span><i>{s}</i>{w}</span>{/each}</div>
        <p><b>Beaten most:</b> {#each d.beaten_most as [o, c], i}{i ? ', ' : ''}{nameOf(o)} ({c}){/each}</p>
        <p><b>Biggest win:</b> by {n(d.biggest.margin)} over {nameOf(d.biggest.opp)}, {d.biggest.season} week {d.biggest.week} ({n(d.biggest.pts)} to {n(d.biggest.opts)})</p>
        <p><b>Closest win:</b> by {n(d.closest.margin)} over {nameOf(d.closest.opp)}, {d.closest.season} week {d.closest.week}</p>
        <p><b>Longest winning streak:</b> {d.longest_streak}. <b>All-time list:</b> {m.rank} of {m.of} in career wins.</p>
    </div>
{/snippet}

{#if mode === 'book' && rw?.through_week}
    <section class="rw book">
        <p class="eyebrow">Record Watch</p>
        <h2>What can still fall this season</h2>
        <p class="sub">{sub} Rebuilt from every game at each update. Season marks are regular season only.</p>

        {#if live.some((r) => r.status === 'broken') || fresh.length}
            <h3>Broken or set this season</h3>
            <div class="grid">
                {#each live.filter((r) => r.status === 'broken') as r}
                    <div class="card hot"><span class="tag">Record broken</span><b class="ttl">{r.title}</b>
                        {#each r.chasers.filter((c) => c.broke) as c}<p>{@render say(`{${c.h}}`)}: {c.text}</p>{/each}
                        <p class="was">Old mark: {@render say(r.record)}</p></div>
                {/each}
                {#each fresh as f}
                    <div class="card" class:hot={f.rank === 1}><span class="tag">{f.rank === 1 ? 'New record' : `No. ${f.rank} all time`}</span><b class="ttl">{f.title}</b><p>{@render say(f.text)}</p></div>
                {/each}
            </div>
        {/if}

        {#if season.some((r) => r.status === 'live') || streaks.some((r) => r.status === 'live')}
            <h3>Within reach</h3>
            <div class="grid">
                {#each [...streaks, ...season].filter((r) => r.status === 'live') as r}
                    <div class="card"><b class="ttl">{r.title}</b>
                        <p class="was">Record: {@render say(r.record)}</p>
                        {#if r.note}<p class="note">{r.note}</p>{/if}
                        {#each r.chasers as c}<p class="ch">{#if avatarOf(c.h)}<img class="av" src={avatarOf(c.h)} alt="" decoding="async" on:error={hideBroken} />{/if}{@render say(`{${c.h}}`)}<span>{c.text}</span></p>{/each}</div>
                {/each}
            </div>
        {/if}

        {#if reached.length || coming.length}
            <h3>Career milestones</h3>
            <div class="grid">
                {#each [...reached, ...coming] as m, i}
                    <div class="card" class:hot={m.reached}><span class="tag">{m.reached ? 'Reached' : 'Coming up'}</span>
                        <b class="ttl">{n(m.mark)} {m.label}</b>
                        <p>{#if avatarOf(m.h)}<img class="av" src={avatarOf(m.h)} alt="" decoding="async" on:error={hideBroken} />{/if}{@render say(m.text)}</p>
                        {#if m.detail}
                            <button class="more" on:click={() => (open[i] = !open[i])}>{open[i] ? 'Hide' : 'How the wins break down'}</button>
                            {#if open[i]}{@render detail(m)}{/if}
                        {/if}</div>
                {/each}
            </div>
        {/if}

        {#if passing.length}
            <h3>The all-time lists</h3>
            <ul class="plain">{#each passing as p}<li>{@render say(p.text)}</li>{/each}</ul>
        {/if}
    </section>
{:else if mode === 'home' && homeLines.length}
    <section class="rw strip">
        <p class="eyebrow">Record Watch</p>
        <ul class="plain">
            {#each homeLines as l}<li>{#if avatarOf(l.h)}<img class="av" src={avatarOf(l.h)} alt="" decoding="async" on:error={hideBroken} />{/if}<span class="tag" class:hottag={l.k === 'broken' || l.k === 'fresh'}>{TAG[l.k]}</span><b class="ttl2">{l.title}.</b> {@render say(l.text)}</li>{/each}
        </ul>
        <a class="all" href="/record-book">Every record in play, in the Record Book</a>
    </section>
{:else if mode === 'news' && newsLines.length}
    <section class="rw strip news">
        <p class="eyebrow">Record Watch</p>
        <ul class="plain">
            {#each newsLines as l}<li>{#if avatarOf(l.h)}<img class="av" src={avatarOf(l.h)} alt="" decoding="async" on:error={hideBroken} />{/if}<span class="tag" class:hottag={l.k === 'broken' || l.k === 'fresh'}>{TAG[l.k]}</span><b class="ttl2">{l.title}.</b> {@render say(l.text)}</li>{/each}
        </ul>
        <a class="all" href="/record-book">Every record in play, in the Record Book</a>
    </section>
{:else if mode === 'manager' && (mine.length || myWins)}
    <section class="rw strip mgr">
        <p class="eyebrow">Record Watch</p>
        <h3 class="mh">Records and milestones in play for {nameOf(handle)}</h3>
        <p class="sub">{sub}</p>
        <ul class="plain">
            {#each mine as l}<li>{#if avatarOf(l.h)}<img class="av" src={avatarOf(l.h)} alt="" decoding="async" on:error={hideBroken} />{/if}<span class="tag" class:hottag={l.k === 'broken' || l.k === 'fresh'}>{TAG[l.k]}</span><b class="ttl2">{l.title}.</b> {@render say(l.text)}</li>{/each}
        </ul>
        {#if myWins}
            <button class="more" on:click={() => (open.me = !open.me)}>{open.me ? 'Hide' : `How the ${n(myWins.value)} career wins break down`}</button>
            {#if open.me}{@render detail(myWins)}{/if}
        {/if}
    </section>
{/if}

<style>
    .rw { text-align: left; background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 12px; }
    .book { margin: 1.2em 0 0.5em; padding: 1.1em 1.2em 1.3em; }
    .strip { max-width: 900px; margin: 1.2em auto; padding: 0.9em 1.1em; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    h2 { margin: 0.1em 0; font-size: 1.3em; color: #ffffff; border: 0; padding: 0; }
    h3 { margin: 1.2em 0 0.5em; font-size: 1em; color: #ffffff; border-bottom: 1px solid #25304a; padding-bottom: 0.3em; }
    h3.mh { margin: 0.1em 0; border: 0; padding: 0; font-size: 1.1em; }
    .sub { color: #aab6cc; font-size: 0.85em; margin: 0.2em 0 0.4em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 0.6em; }
    .card { background: #0d1320; border: 1px solid #25304a; border-radius: 10px; padding: 0.7em 0.8em; font-size: 0.88em; line-height: 1.45; min-width: 0; }
    .card.hot { border-color: #2ecc71; box-shadow: inset 3px 0 0 #2ecc71; }
    .card p { margin: 0.3em 0 0; }
    .ttl { display: block; color: #ffffff; font-size: 1.05em; }
    .ttl2 { color: #ffffff; }
    .was { color: #aab6cc; }
    .note { color: #ffb37a; font-size: 0.92em; }
    .ch { border-top: 1px solid #25304a; padding-top: 0.35em; }
    .ch span { display: block; color: #d5dceb; }
    .tag { display: inline-block; padding: 0 0.5em; border-radius: 3px; background: #24406e; color: #ffffff; font-size: 0.74em; font-weight: 700; margin: 0 0.4em 0.25em 0; text-transform: uppercase; letter-spacing: 0.04em; }
    .card.hot .tag, .hottag { background: #1e8449; }
    .nm { color: #ffffff; font-weight: 700; text-decoration: none; }
    a.nm:hover { color: #ff9a5c; }
    .plain { list-style: none; margin: 0.4em 0 0; padding: 0; }
    .plain li { font-size: 0.9em; line-height: 1.5; padding: 0.4em 0; border-bottom: 1px solid #25304a; color: #d5dceb; }
    .plain li:last-child { border-bottom: 0; }
    .all { display: inline-block; margin-top: 0.5em; color: #ff9a5c; font-weight: 700; font-size: 0.88em; }
    .more { margin-top: 0.5em; padding: 0.25em 0.7em; font-size: 0.85em; cursor: pointer; background: #24406e; color: #ffffff; border: 1px solid #35579a; border-radius: 6px; }
    .detail { margin-top: 0.5em; font-size: 0.95em; color: #d5dceb; }
    .detail p { margin: 0.35em 0 0; }
    .detail b { color: #ffffff; }
    .bys { display: flex; flex-wrap: wrap; gap: 0.3em; margin-top: 0.3em; }
    .bys span { background: #1a2438; border: 1px solid #25304a; border-radius: 6px; padding: 0.1em 0.45em; font-weight: 700; color: #ffffff; font-variant-numeric: tabular-nums; }
    .bys i { font-style: normal; font-weight: 400; color: #aab6cc; margin-right: 0.35em; font-size: 0.85em; }
    .av { width: 22px; height: 22px; border-radius: 50%; object-fit: cover; vertical-align: middle; margin-right: 0.4em; background: #0b101c; }
</style>
