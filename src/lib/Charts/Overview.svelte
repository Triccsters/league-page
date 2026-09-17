<script>
    // A hand-written block of prose, from src/lib/data/overviews_extra.json.
    // The weekly build never touches that file, so anything written there
    // survives every refresh. Renders nothing at all when there is no text,
    // which is what makes it safe to drop onto every manager and every season
    // before they have all been written.
    export let text = '';
    export let heading = '';
    export let kicker = '';

    // blank line between paragraphs, same convention as the recap "intro" field
    $: paras = (text || '').split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
</script>

{#if paras.length}
    <section class="ov">
        {#if heading}
            <h3>{heading}{#if kicker}<small>{kicker}</small>{/if}</h3>
        {/if}
        {#each paras as p}
            <p>{p}</p>
        {/each}
    </section>
{/if}

<style>
    .ov {
        max-width: 900px;
        margin: 1.4em auto 0;
        padding: 0.9em 1.1em;
        text-align: left;
        border-left: 3px solid #3498db;
        background: rgba(52, 152, 219, 0.07);
        border-radius: 0 9px 9px 0;
    }
    h3 {
        margin: 0 0 0.45em;
        font-size: 0.82em;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.7;
    }
    h3 small {
        text-transform: none;
        letter-spacing: 0;
        font-weight: 400;
        opacity: 0.8;
        margin-left: 0.5em;
    }
    p {
        margin: 0 0 0.7em;
        font-size: 0.95em;
        line-height: 1.55;
    }
    p:last-child { margin-bottom: 0; }
</style>
