<script>
    // What's new on the site (T.J., 2026-11-12): additions and fixes, newest first.
    // The list is src/lib/data/whatsnew.json, written per league from
    // _shared/site2/whatsnew.json by _shared/install_whatsnew.py.
    import items from '$lib/data/whatsnew.json';

    const SHOW = 4;
    const list = [...(items || [])].sort((a, b) => (a.d < b.d ? 1 : a.d > b.d ? -1 : 0));
    let all = false;
    $: shown = all ? list : list.slice(0, SHOW);
    const day = (d) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
</script>

{#if list.length}
    <section class="wn">
        <h3>What's new on the site</h3>
        <ul>
            {#each shown as it}
                <li>
                    <span class="tag" class:fix={it.kind === 'fix'}>{it.kind === 'fix' ? 'Fixed' : 'New'}</span>
                    <span class="when">{day(it.d)}</span>
                    <b>{it.title}.</b>
                    {it.text}
                    {#if it.link}<a href={it.link}>See it</a>{/if}
                </li>
            {/each}
        </ul>
        {#if list.length > SHOW}
            <button on:click={() => (all = !all)}>{all ? 'Show fewer' : `Show all ${list.length}`}</button>
        {/if}
    </section>
{/if}

<style>
    .wn { max-width: 900px; margin: 2em auto 1em; padding: 0.9em 1.1em; text-align: left;
          border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; }
    h3 { margin: 0 0 0.5em; font-size: 1em; }
    ul { list-style: none; margin: 0; padding: 0; }
    li { font-size: 0.9em; line-height: 1.5; padding: 0.4em 0; border-bottom: 1px solid rgba(127,127,127,0.2); }
    li:last-child { border-bottom: 0; }
    .tag { display: inline-block; padding: 0 0.45em; border-radius: 3px; background: #1e8449; color: #ffffff;
           font-size: 0.78em; font-weight: 700; margin-right: 0.35em; }
    .tag.fix { background: #2471a3; }
    .when { opacity: 0.7; font-size: 0.85em; margin-right: 0.35em; }
    a { margin-left: 0.3em; font-weight: 600; }
    button { margin-top: 0.5em; padding: 0.25em 0.7em; font-size: 0.85em; cursor: pointer; }
</style>
