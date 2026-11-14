<script>
    // "Jump to section" row for long pages (T.J., 2026-11-13). Sits in the layout and builds
    // itself from the page's own h2 headings, so no page needs editing. Shows only when a
    // page has four or more sections. Pages that load their data late are re-read a few times.
    import { onMount, onDestroy } from 'svelte';
    import { page } from '$app/stores';

    let items = [];
    let timers = [];
    const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);

    function scan() {
        const hs = [...document.querySelectorAll('main h2')].filter((h) => !h.closest('nav, footer, .jumpto') && h.offsetParent !== null);
        const seen = {};
        const out = [];
        for (const h of hs) {
            const text = (h.innerText || '').replace(/\s+/g, ' ').trim();
            if (!text || text.length > 60) continue;
            if (!h.id) {
                let id = slug(text) || 'section';
                seen[id] = (seen[id] || 0) + 1;
                if (seen[id] > 1) id += '-' + seen[id];
                h.id = id;
            }
            h.style.scrollMarginTop = '5em';
            out.push({ id: h.id, text });
        }
        items = out.length >= 4 ? out : [];
    }
    function rescan() {
        timers.forEach(clearTimeout);
        items = [];
        timers = [300, 1500, 4000, 9000].map((ms) => setTimeout(scan, ms));
    }
    let unsub;
    onMount(() => { unsub = page.subscribe(() => rescan()); });
    onDestroy(() => { timers.forEach(clearTimeout); if (unsub) unsub(); });
</script>

{#if items.length && $page.url.pathname !== '/'}
    <div class="jumpto">
        <span>Jump to</span>
        {#each items as it}<a href="#{it.id}">{it.text}</a>{/each}
    </div>
{/if}

<style>
    .jumpto { max-width: 1040px; margin: 0.8em auto 0; padding: 0.5em 1em; display: flex; flex-wrap: wrap; gap: 0.4em; align-items: center; justify-content: center; }
    span { font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin-right: 0.3em; }
    a { font-size: 0.85em; padding: 0.2em 0.7em; border: 1px solid rgba(127,127,127,0.4); border-radius: 14px; text-decoration: none; color: inherit; white-space: nowrap; }
    a:hover { border-color: #3498db; color: #3498db; }
</style>
