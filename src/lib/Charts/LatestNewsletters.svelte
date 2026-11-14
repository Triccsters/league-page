<script>
    // Latest newsletter issues on the home page, right under What's new (T.J., 2026-11-13).
    import { newsletters } from '$lib/utils/newsletters';
    const list = [...newsletters].sort((a, b) => (a.slug < b.slug ? 1 : -1)).slice(0, 3);
    const label = (n) => {
        const m = String(n.slug).match(/(\d{4}).*?(\d{1,2})$/);
        return n.week ? `Week ${n.week}` : m ? `Week ${parseInt(m[2])}` : n.slug;
    };
</script>

{#if list.length}
    <section class="nl">
        <div class="top"><h3>Weekly newsletter</h3><a href="/recaps">Every issue</a></div>
        <div class="row">
            {#each list as n, i}
                <a class="card" class:latest={i === 0} href="/recaps/{n.slug}">
                    <span class="wk">{label(n)}{#if i === 0}<em>Latest</em>{/if}</span>
                    <b>{n.headline}</b>
                    {#if n.dek}<small>{n.dek}</small>{/if}
                </a>
            {/each}
        </div>
    </section>
{/if}

<style>
    .nl { max-width: 1000px; margin: 1em auto; padding: 0 1em; }
    .top { display: flex; justify-content: space-between; align-items: baseline; }
    h3 { margin: 0 0 0.5em; }
    .top a { color: #3498db; font-size: 0.9em; }
    .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.8em; }
    .card { display: flex; flex-direction: column; gap: 0.3em; padding: 0.8em 1em; border: 1px solid rgba(127,127,127,0.35); border-radius: 8px; text-decoration: none; color: inherit; }
    .card:hover { border-color: #3498db; }
    .card.latest { border-color: #f1c40f; }
    .wk { font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.8; }
    .wk em { font-style: normal; background: #f1c40f; color: #111; border-radius: 8px; padding: 0 0.5em; margin-left: 0.5em; font-weight: 700; }
    small { opacity: 0.75; line-height: 1.35; }
</style>
