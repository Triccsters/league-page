<script>
    // Losses where one starter came in under his own normal by more than the
    // margin of defeat. Not an injury claim — just the collapse, with the number.
    import { onMount } from 'svelte';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';

    export let handle;

    let data = null;
    onMount(async () => {
        try {
            const r = await fetch('/data/costly.json');
            if (r.ok) data = await r.json();
        } catch (e) {
            data = null;
        }
    });

    $: mine = (data?.byManager?.[handle] ?? []).slice(0, 5);
</script>

{#if mine.length}
    <section class="cg">
        <h3>Games that got away</h3>
        <p class="sub">
            Losses where one starter came in under his own average for that season by more than the
            margin of defeat. It says the game turned on that player, not why.
        </p>
        {#each mine as c}
            <div class="row">
                <span class="when">{c.season}<small>wk {c.week}</small></span>
                <span class="what">
                    <b>{c.n}</b> <small>{c.p}</small>
                    scored <b class="bad">{c.pts}</b> against a {c.avg} average
                    <small class="vs">
                        lost {c.lost}–{c.won} to
                        {#if managerLink(c.vs)}<a href={managerLink(c.vs)}>{nameOf(c.vs)}</a>{:else}{nameOf(c.vs)}{/if}
                        {#if c.playoff}· {c.label}{/if}
                    </small>
                </span>
                <span class="gap">−{c.short}</span>
            </div>
        {/each}
    </section>
{/if}

<style>
    .cg { max-width: 900px; margin: 1.4em auto 0; padding: 0 1em; text-align: left; }
    h3 { margin: 0 0 0.1em; font-size: 1em; }
    .sub { opacity: 0.68; font-size: 0.8em; margin: 0 0 0.5em; max-width: 52em; }
    .row { display: grid; grid-template-columns: 4.2em 1fr auto; gap: 0.6em; align-items: baseline;
           padding: 0.35em 0; border-bottom: 1px solid rgba(127,127,127,0.18); font-size: 0.9em; }
    .when { font-variant-numeric: tabular-nums; opacity: 0.75; }
    .when small { display: block; opacity: 0.7; font-size: 0.78em; }
    .what small { opacity: 0.65; font-size: 0.8em; }
    .what small.vs { display: block; }
    .bad { color: #e74c3c; }
    .gap { font-weight: 700; font-variant-numeric: tabular-nums; color: #e74c3c; }
    a { color: #3498db; }
</style>
