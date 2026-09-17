<script>
    // Award badges for one manager: every top-three finish in the trophy case.
    import { onMount } from 'svelte';

    export let handle;

    let awards = null;
    onMount(async () => {
        try {
            const r = await fetch('/data/awards.json');
            if (r.ok) awards = await r.json();
        } catch (e) {
            awards = null;
        }
    });

    const MEDAL = ['🥇', '🥈', '🥉'];
    const fmt = (a, v) => (a.fmt || '{v}').replace('{v}', v);

    // rank comes from where the manager sits on that award's podium
    $: mine = !awards ? [] : awards.awards
        .map(a => {
            const i = a.podium.findIndex(p => p.h === handle);
            return i < 0 ? null : { a, rank: i, p: a.podium[i] };
        })
        .filter(Boolean)
        .sort((x, y) => x.rank - y.rank || y.a.podium.length - x.a.podium.length);
</script>

{#if mine.length}
    <section class="badges">
        <h3>Awards</h3>
        <div class="wrap">
            {#each mine as m}
                <a class="badge" class:gold={m.rank === 0} href="/awards" title="{m.a.note}">
                    <span class="em">{m.a.emoji}</span>
                    <span class="txt">
                        <b>{m.a.name}</b>
                        <small>{MEDAL[m.rank]} {fmt(m.a, m.p.v)}{m.p.note ? ` · ${m.p.note}` : ''}</small>
                    </span>
                </a>
            {/each}
        </div>
    </section>
{/if}

<style>
    .badges { max-width: 900px; margin: 1.2em auto 0; padding: 0 1em; text-align: left; }
    h3 { margin: 0 0 0.4em; font-size: 1em; }
    .wrap { display: flex; flex-wrap: wrap; gap: 0.5em; }
    .badge { display: flex; align-items: center; gap: 0.5em; text-decoration: none; color: inherit;
             border: 1px solid rgba(127,127,127,0.3); border-radius: 999px; padding: 0.3em 0.8em 0.3em 0.55em; }
    .badge.gold { border-color: rgba(241,196,15,0.75); background: rgba(241,196,15,0.1); }
    .em { font-size: 1.25em; line-height: 1; }
    .txt b { display: block; font-size: 0.85em; font-weight: 600; }
    .txt small { display: block; opacity: 0.7; font-size: 0.75em; }
    @media (max-width: 500px) {
        .wrap { gap: 0.4em; }
        .badge { padding: 0.25em 0.6em 0.25em 0.45em; }
    }
</style>
