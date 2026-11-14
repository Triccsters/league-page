<script>
    // Rule ideas the league could vote on. The list is src/lib/data/rule_ideas.json in each league's own repo,
    // so each league has its own list. Voting is a Google Form (leagueInfo.rulesForm). T.J., 2026-11-13.
    import * as leagueInfo from '$lib/utils/leagueInfo';
    import ideas from '$lib/data/rule_ideas.json';
    const form = leagueInfo.rulesForm || null;
    const embed = form ? (form.includes('embedded=true') ? form : form + (form.includes('?') ? '&' : '?') + 'embedded=true') : null;
    const STATUS = { idea: 'Idea', researching: 'Being looked into', vote: 'Up for a vote', passed: 'Passed', dropped: 'Dropped' };
    const list = (ideas.ideas || []).filter((i) => i.status !== 'hidden');
</script>

<svelte:head><title>Rule Ideas | {leagueInfo.leagueName || 'League'}</title></svelte:head>

<div class="holder">
    <h1>Rule Ideas</h1>
    <p class="sub">
        Things other leagues do that we could try. <b>Nothing here is a rule.</b> It is a list of ideas, and nothing
        changes without a league vote.
    </p>

    {#if list.length}
        <div class="cards">
            {#each list as i}
                <section class="card">
                    <h3>{i.title}<span class="st s-{i.status || 'idea'}">{STATUS[i.status] || 'Idea'}</span></h3>
                    <p>{i.what}</p>
                    {#if i.why}<p class="why"><b>Why:</b> {i.why}</p>{/if}
                    {#if i.catch}<p class="why"><b>The catch:</b> {i.catch}</p>{/if}
                </section>
            {/each}
        </div>
    {:else}
        <p class="sub">No ideas listed yet.</p>
    {/if}

    <h2>Vote</h2>
    {#if embed}
        <div class="form"><iframe src={embed} title="Rule ideas vote" loading="lazy">Loading the form…</iframe></div>
        <p class="lead"><a href={form} target="_blank" rel="noopener">Open the form in its own tab</a></p>
    {:else}
        <p class="lead soon">Voting opens here soon. Until then, tell the commissioner what you think.</p>
    {/if}
</div>

<style>
    .holder { max-width: 900px; margin: 0 auto; padding: 1em; }
    h1 { text-align: center; margin: 0.6em 0 0.2em; }
    h2 { text-align: center; margin: 1.6em 0 0.4em; }
    .sub, .lead { text-align: center; opacity: 0.85; max-width: 720px; margin: 0.2em auto 1em; line-height: 1.5; }
    .soon { border: 1px dashed rgba(127,127,127,0.5); border-radius: 10px; padding: 1em; }
    .cards { display: grid; gap: 0.8em; }
    .card { border: 1px solid rgba(127,127,127,0.3); border-radius: 12px; padding: 0.9em 1.1em; background: rgba(127,127,127,0.06); }
    .card h3 { margin: 0 0 0.35em; display: flex; flex-wrap: wrap; align-items: center; gap: 0.6em; }
    .card p { margin: 0.3em 0 0; line-height: 1.5; opacity: 0.92; }
    .why { font-size: 0.92em; opacity: 0.8; }
    .st { font-size: 0.65em; font-weight: 700; color: #fff; border-radius: 999px; padding: 0.15em 0.7em; background: #566573; }
    .s-researching { background: #7d6608; } .s-vote { background: #2471a3; } .s-passed { background: #1e8449; } .s-dropped { background: #7b241c; }
    .form { max-width: 720px; margin: 0 auto; border-radius: 12px; overflow: hidden; background: #fff; }
    .form iframe { width: 100%; height: 1400px; border: 0; display: block; }
    a { color: inherit; }
</style>
