<script>
    // The week read as a short list of titles. Built in update_site.py.
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    export let awards = [];
</script>

{#if awards && awards.length}
    <section class="wa">
        <h3>Week awards</h3>
        <div class="wrap">
            {#each awards as a (a.key)}
                <div class="card" class:mine={a.manager === $myTeam}>
                    <span class="em">{a.emoji}</span>
                    <div class="txt">
                        <b>{a.name}</b>
                        <span class="who">
                            {#if managerLink(a.manager)}
                                <a href={managerLink(a.manager)}>{nameOf(a.manager)}</a>
                            {:else}{nameOf(a.manager)}{/if}
                            <em>{a.value}</em>
                        </span>
                        {#if a.vs}<small>over {nameOf(a.vs)}</small>{/if}
                        {#if a.note}<small>{a.note}</small>{/if}
                    </div>
                </div>
            {/each}
        </div>
    </section>
{/if}

<style>
    .wa { max-width: 900px; margin: 1.2em auto; padding: 0 1em; text-align: left; }
    h3 { margin: 0 0 0.4em; font-size: 1em; }
    .wrap { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.6em; }
    .card { display: flex; gap: 0.55em; align-items: flex-start;
            border: 1px solid rgba(127,127,127,0.28); border-radius: 9px; padding: 0.5em 0.7em; }
    .card.mine { border-color: rgba(52,152,219,0.6); background: rgba(52,152,219,0.1); }
    .em { font-size: 1.4em; line-height: 1.1; }
    .txt b { display: block; font-size: 0.82em; opacity: 0.75; font-weight: 600; }
    .who { display: block; font-size: 0.95em; }
    .who em { font-style: normal; font-weight: 700; margin-left: 0.35em; font-variant-numeric: tabular-nums; }
    .who a { color: #3498db; }
    small { display: block; opacity: 0.6; font-size: 0.75em; margin-top: 0.1em; }
</style>
