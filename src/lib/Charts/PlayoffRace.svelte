<script>
    // Playoff race at a glance: stat tiles, a status symbol per team, and a card per team with the games left.
    // Layout idea from crunchtimefantasy.com's Playoff Push (T.J., 2026-11-13). Status comes from the playoff
    // simulation in odds.json, so "in" and "out" mean every simulated season, not a mathematical clinch.
    import { onMount } from 'svelte';
    import odds from '$lib/data/odds.json';
    import { nameOf, managerLink } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });
    const teams = [...(odds.teams || [])].sort((a, b) => b.playoff - a.playoff || b.w - a.w || b.pf - a.pf);
    const weeks = odds.remaining_weeks || [];
    const status = (t) => (t.playoff >= 100 ? 'in' : t.playoff <= 0 ? 'out' : 'alive');
    const SYM = { in: '✓', alive: '◉', out: '✕' };
    const WORD = { in: 'In, in every simulation', alive: 'Alive', out: 'Out, in every simulation' };
    const n = (k) => teams.filter((t) => status(t) === k).length;
    const pct = (v) => (v >= 100 ? '100%' : v <= 0 ? '0%' : v < 1 ? '<1%' : v > 99 ? '>99%' : `${Math.round(v)}%`);
    const tiles = [
        [odds.playoff_teams, 'playoff spots'],
        [weeks.length, weeks.length === 1 ? 'week left' : 'weeks left'],
        [n('in'), 'locked in'],
        [n('alive'), 'still alive'],
        [n('out'), 'out of it'],
    ];
</script>

{#if teams.length && weeks.length}
    <section class="pr">
        <div class="tiles">{#each tiles as [v, label]}<div><b>{v}</b><span>{label}</span></div>{/each}</div>
        <p class="key"><span class="s in">✓</span> made it in every one of {Number(odds.sims).toLocaleString('en-US')} simulated seasons · <span class="s alive">◉</span> still alive · <span class="s out">✕</span> missed in every one. Not a mathematical clinch.</p>
        <h2>Every team, one race</h2>
        <div class="cards">
            {#each teams as t (t.h)}
                {@const st = status(t)}
                <article class="card {st}" class:mine={ready && t.h === $myTeam}>
                    <header>
                        <span class="s {st}" title={WORD[st]}>{SYM[st]}</span>
                        <a href={managerLink(t.h) || undefined}>{nameOf(t.h)}</a>
                        <b>{pct(t.playoff)}</b>
                    </header>
                    <p class="line">{t.w}-{t.l} · {Math.round(t.pf).toLocaleString('en-US')} points for · projected {t.proj_w} wins</p>
                    <ul>
                        {#each t.rest_opponents || [] as o, i}<li><span>Wk {weeks[i] ?? ''}</span>{nameOf(o)}</li>{/each}
                    </ul>
                    <p class="out">Win out: {t.w + (t.rest_opponents || []).length}-{t.l}{t.bye > 0 && t.bye < 100 ? ` · bye ${pct(t.bye)}` : ''}{t.title >= 1 ? ` · title ${pct(t.title)}` : ''}</p>
                </article>
            {/each}
        </div>
    </section>
{/if}

<style>
    .pr { margin: 1em 0 1.5em; text-align: left; }
    .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 0.6em; }
    .tiles div { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 12px; padding: 0.7em; text-align: center; }
    .tiles b { display: block; font-size: 1.9em; line-height: 1.1; color: #fff; }
    .tiles span { font-size: 0.72em; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.75; }
    .key { font-size: 0.85em; opacity: 0.8; text-align: center; margin: 0.8em 0 0; }
    h2 { margin: 1.2em 0 0.6em; }
    .s { display: inline-block; width: 1.5em; height: 1.5em; line-height: 1.5em; text-align: center; border-radius: 50%; font-weight: 800; color: #fff; font-size: 0.9em; }
    .s.in { background: #1e8449; } .s.alive { background: #2471a3; } .s.out { background: #a93226; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 0.7em; }
    .card { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 12px; padding: 0.8em 0.9em; }
    .card.in { border-color: #1e8449; } .card.out { opacity: 0.75; }
    .card.mine { box-shadow: inset 0 0 0 2px #2ecc71; }
    header { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 0.5em; }
    header a { color: #fff; font-weight: 800; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    header b { font-size: 1.2em; }
    .line { font-size: 0.82em; opacity: 0.8; margin: 0.4em 0; }
    ul { list-style: none; margin: 0; padding: 0; font-size: 0.86em; }
    li { display: flex; gap: 0.6em; padding: 0.18em 0; border-top: 1px solid #25304a; }
    li span { opacity: 0.6; min-width: 3.2em; }
    .out { font-size: 0.82em; font-weight: 700; margin: 0.5em 0 0; color: #ffb37a; }
</style>
