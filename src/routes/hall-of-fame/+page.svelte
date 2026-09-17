<script>
    // Trophy case. Every award is computed from league data in scripts/awards.py.
    import { onMount } from 'svelte';
    import { nameOf, managerLink, teamName, site } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let data = null;
    let failed = false;
    let ready = false;
    let only = 'all';

    onMount(async () => {
        ready = true;
        try {
            const r = await fetch('/data/awards.json');
            if (!r.ok) throw new Error(r.status);
            data = await r.json();
        } catch (e) {
            failed = true;
        }
    });

    const GROUPS = {
        all: 'Everything',
        winning: 'Winning',
        wheeling: 'Wheeling and dealing',
        scoring: 'Scoring',
        luck: 'Luck and heartbreak',
    };
    const GROUP_OF = {
        titles: 'winning', winpct: 'winning', playoffs: 'winning', ironman: 'winning', toilet: 'winning',
        trader: 'wheeling', dealmaker: 'wheeling', waiver: 'wheeling', pickup: 'wheeling',
        faab: 'wheeling', active: 'wheeling', drafter: 'wheeling', steal: 'wheeling',
        points: 'scoring', bigweek: 'scoring', big150: 'scoring', steady: 'scoring', swings: 'scoring',
        lucky: 'luck', unlucky: 'luck', heartbreak: 'luck', escape: 'luck',
    };

    const fmt = (a, v) => (a.fmt || '{v}').replace('{v}', v);
    const MEDAL = ['🥇', '🥈', '🥉'];

    $: awards = !data ? [] : data.awards.filter(a => only === 'all' || GROUP_OF[a.key] === only);
</script>

<div class="holder">
    <h1>Awards</h1>
    <p class="sub">
        Every award here is worked out from the league's own record: game scores, trades, waiver claims and draft
        picks, across all {site.first_season ? `seasons since ${site.first_season}` : 'seasons on record'}. Nothing is
        voted on. Top three in each, with the leader's detail where there is one.
    </p>

    {#if data}
        <div class="filters">
            <select bind:value={only}>
                {#each Object.entries(GROUPS) as [k, label]}<option value={k}>{label}</option>{/each}
            </select>
        </div>

        <div class="cards">
            {#each awards as a (a.key)}
                <section class="card">
                    <h2><span class="em">{a.emoji}</span>{a.name}</h2>
                    <p class="note">{a.note}</p>
                    <ol>
                        {#each a.podium as p, i}
                            <li class:mine={ready && p.h === $myTeam}>
                                <span class="medal">{MEDAL[i]}</span>
                                <span class="who">
                                    {#if managerLink(p.h)}<a href={managerLink(p.h)}>{nameOf(p.h)}</a>{:else}{nameOf(p.h)}{/if}
                                    {#if p.note}<small>{p.note}</small>{/if}
                                </span>
                                <span class="val">{fmt(a, p.v)}</span>
                            </li>
                        {:else}
                            <li class="empty">Not enough data yet.</li>
                        {/each}
                    </ol>
                </section>
            {/each}
        </div>

        <p class="foot">
            Rebuilt every time the site data is refreshed, so these move during the season.
            Career awards need three seasons before a manager qualifies.
            {#if site.first_season && site.first_season < 2014}
                Seasons before 2014 were played on Yahoo under standard scoring, so counting awards
                include them while the points ran lower than they do now.
            {/if}
        </p>
    {:else if failed}
        <p class="err">Awards could not be loaded.</p>
    {:else}
        <p class="sub">Loading…</p>
    {/if}
</div>

<style>
    .holder { max-width: 1100px; margin: 0 auto 3em; padding: 0 1em; text-align: left; }
    h1 { margin-bottom: 0.2em; }
    .sub { opacity: 0.75; font-size: 0.9em; max-width: 60em; }
    .filters { margin: 1.2em 0 0.6em; }
    select { padding: 0.35em 0.5em; font-size: 0.9em; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1em; }
    .card { border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; padding: 0.8em 0.9em 0.6em; }
    .card h2 { font-size: 1em; margin: 0 0 0.1em; display: flex; align-items: center; gap: 0.45em; }
    .em { font-size: 1.3em; line-height: 1; }
    .note { opacity: 0.65; font-size: 0.8em; margin: 0 0 0.6em; }
    ol { list-style: none; margin: 0; padding: 0; }
    li { display: grid; grid-template-columns: 1.6em 1fr auto; align-items: center; gap: 0.4em;
         padding: 0.28em 0.3em; border-radius: 6px; font-size: 0.92em; }
    li + li { border-top: 1px solid rgba(127,127,127,0.16); }
    li.mine { background: rgba(52,152,219,0.14); }
    .medal { font-size: 1em; }
    .who a { color: #3498db; }
    .who small { display: block; opacity: 0.6; font-size: 0.78em; }
    .val { font-weight: 700; font-variant-numeric: tabular-nums; }
    .empty { opacity: 0.6; font-size: 0.85em; grid-template-columns: 1fr; }
    .foot { opacity: 0.6; font-size: 0.8em; margin-top: 1.5em; }
    .err { color: #e74c3c; }
    @media (max-width: 500px) {
        .cards { grid-template-columns: 1fr; }
    }
</style>
