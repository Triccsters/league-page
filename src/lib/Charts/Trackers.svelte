<script>
    // Season storylines and trackers, built at the Tuesday update by
    // scripts/trackers.py. Every tracker is a card of rows; a cell written
    // "@@handle" is a team.
    import { onMount } from 'svelte';
    import data from '$lib/data/trackers.json';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });
    const groups = data?.groups || [];
    let open = groups.length ? groups[0].id : null;
    const isTeam = (c) => typeof c === 'string' && c.startsWith('@@');
    const h = (c) => c.slice(2);
    const mineRow = (row, me) => me && row.some((c) => isTeam(c) && h(c) === me);
</script>

<div class="tr">
    <h1>League Trackers <small>after week {data.through_week}</small></h1>
    <p class="lede">Storylines, races and the numbers behind the trade talk. Rebuilt every Tuesday.</p>
    {#if groups.length}
        <nav class="tabs">
            {#each groups as g (g.id)}
                <button class:on={open === g.id} on:click={() => (open = g.id)}>{g.title}</button>
            {/each}
        </nav>
        {#each groups as g (g.id)}
            {#if open === g.id}
                <p class="intro">{g.intro}</p>
                <div class="cards">
                    {#each g.cards as c (c.id)}
                        <section class="card" id={c.id}>
                            <h2>{c.title}{#if c.race}<span class="tag">Race</span>{/if}</h2>
                            <p class="note">{c.note}</p>
                            <div class="scroll">
                                <table>
                                    <thead><tr>{#each c.cols as col}<th>{col}</th>{/each}</tr></thead>
                                    <tbody>
                                        {#each c.rows as row, i}
                                            <tr class:mine={ready && mineRow(row, $myTeam)} class:lead={c.race && i === 0}>
                                                {#each row as cell}
                                                    <td>
                                                        {#if isTeam(cell)}
                                                            {#if managerLink(h(cell))}<a href={managerLink(h(cell))}>{nameOf(h(cell))}</a>{:else}{nameOf(h(cell))}{/if}
                                                        {:else}{cell}{/if}
                                                    </td>
                                                {/each}
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    {/each}
                </div>
            {/if}
        {/each}
        <p class="foot">Projections: {data.projections}, scored with this league's own settings. Points and lineups: this season's matchups.</p>
    {:else}
        <p class="lede">The trackers fill in after the first Tuesday update of the season.</p>
    {/if}
</div>

<style>
    .tr { max-width: 1100px; margin: 1.5em auto 3em; padding: 0 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    h1 small { font-size: 0.5em; font-weight: 400; opacity: 0.7; }
    .lede, .intro { text-align: center; opacity: 0.85; }
    .intro { font-style: italic; margin: 0.4em 0 1em; }
    .tabs { display: flex; flex-wrap: wrap; justify-content: center; gap: 0.4em; margin: 1em 0 0.4em; }
    .tabs button { font: inherit; padding: 0.4em 0.9em; border-radius: 999px; border: 1px solid rgba(127,127,127,0.45); background: none; color: inherit; cursor: pointer; }
    .tabs button.on { background: #27ae60; border-color: #27ae60; color: #fff; font-weight: 700; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 460px), 1fr)); gap: 1em; }
    .card { border: 1px solid rgba(127,127,127,0.3); border-radius: 10px; padding: 0.8em 0.9em; min-width: 0; }
    h2 { font-size: 1.1em; margin: 0 0 0.2em; display: flex; align-items: center; gap: 0.5em; }
    .tag { font-size: 0.65em; font-weight: 700; border: 1px solid #e67e22; color: #e67e22; border-radius: 999px; padding: 0.05em 0.5em; }
    .note { font-size: 0.82em; opacity: 0.8; margin: 0 0 0.6em; line-height: 1.45; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
    th { text-align: left; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.03em; opacity: 0.7; padding: 0.3em 0.4em; border-bottom: 1px solid rgba(127,127,127,0.35); white-space: nowrap; }
    td { padding: 0.32em 0.4em; border-bottom: 1px solid rgba(127,127,127,0.15); }
    td a { color: inherit; font-weight: 600; }
    tr.lead td { font-weight: 700; }
    tr.mine td { background: rgba(39,174,96,0.14); }
    .foot { text-align: center; font-size: 0.8em; opacity: 0.7; margin-top: 1.5em; }
</style>
