<script>
    // Champions by season with runner-up and third place, worked out from the playoff games in
    // history.json. "Upset" = the champion had the worse regular-season record of the two finalists.
    // Layout idea from great8.org's champions page (T.J., 2026-11-13).
    import { onMount } from 'svelte';
    import { games, nameOf, managerLink, teamName } from '$lib/utils/flpHistory';
    import { myTeam } from '$lib/utils/myTeam';

    let ready = false;
    onMount(() => { ready = true; });

    const rec = {};
    for (const g of games) {
        if (g.playoff || g.pa == null || g.pb == null) continue;
        for (const [me, mine, theirs] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
            const r = (rec[`${g.season}|${me}`] ||= { w: 0, l: 0, t: 0 });
            if (mine > theirs) r.w++; else if (mine < theirs) r.l++; else r.t++;
        }
    }
    const recOf = (s, h) => rec[`${s}|${h}`] || null;
    const recText = (r) => (r ? `${r.w}-${r.l}${r.t ? `-${r.t}` : ''}` : '');
    const pctOf = (r) => (r && r.w + r.l + r.t ? (r.w + r.t / 2) / (r.w + r.l + r.t) : null);
    const split = (g) => (g.pa >= g.pb ? [g.a, g.b, g.pa, g.pb] : [g.b, g.a, g.pb, g.pa]);

    const years = [];
    for (const g of games) {
        if (g.label !== 'Championship' || g.pa == null || g.pb == null || g.pa === g.pb) continue;
        const [champ, runner, cs, rs] = split(g);
        const third = games.find((x) => x.season === g.season && x.label === '3rd place' && x.pa != null && x.pb != null && (x.pa || x.pb));
        const cr = recOf(g.season, champ), rr = recOf(g.season, runner);
        const cp = pctOf(cr), rp = pctOf(rr);
        years.push({
            season: g.season, champ, runner, cs, rs, cr, rr,
            third: third ? split(third)[0] : null,
            upset: cp != null && rp != null && cp < rp,
        });
    }
    years.sort((x, y) => y.season - x.season);

    const tally = {};
    for (const y of years) {
        (tally[y.champ] ||= { t: 0, r: 0, th: 0 }).t++;
        (tally[y.runner] ||= { t: 0, r: 0, th: 0 }).r++;
        if (y.third) (tally[y.third] ||= { t: 0, r: 0, th: 0 }).th++;
    }
    const rings = Object.entries(tally).filter(([, v]) => v.t).sort((x, y) => y[1].t - x[1].t || y[1].r - x[1].r);
    const upsets = years.filter((y) => y.upset).length;
</script>

{#if years.length}
    <section class="ch">
        <h2>Champions</h2>
        <p class="sub">{years.length} title games on record{upsets ? `, ${upsets} won by the finalist with the worse regular-season record` : ''}.</p>
        <div class="rings">
            {#each rings as [h, v]}
                <a class="ring" class:mine={ready && h === $myTeam} href={managerLink(h) || undefined}>
                    <span class="cups">{'🏆'.repeat(Math.min(v.t, 6))}</span>
                    <b>{v.t}</b>
                    <span class="nm">{nameOf(h)}</span>
                </a>
            {/each}
        </div>
        <div class="wrap">
            <table>
                <thead><tr><th>Year</th><th>🏆 Champion</th><th>Final</th><th>🥈 Runner-up</th><th>🥉 Third</th></tr></thead>
                <tbody>
                    {#each years as y (y.season)}
                        <tr>
                            <td class="yr">{y.season}</td>
                            <td class:mine={ready && y.champ === $myTeam}>
                                <b>{nameOf(y.champ)}</b>
                                {#if teamName(y.season, y.champ)}<span class="tn">{teamName(y.season, y.champ)}</span>{/if}
                                <span class="rc">{recText(y.cr)} regular season</span>
                                {#if y.upset}<span class="upset">Upset! Beat {nameOf(y.runner)} ({recText(y.rr)})</span>{/if}
                            </td>
                            <td class="fin">{y.cs.toFixed(2)} to {y.rs.toFixed(2)}</td>
                            <td class:mine={ready && y.runner === $myTeam}>{nameOf(y.runner)}<span class="rc">{recText(y.rr)}</span></td>
                            <td class:mine={ready && y.third === $myTeam}>{y.third ? nameOf(y.third) : ''}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    </section>
{/if}

<style>
    .ch { max-width: 1000px; margin: 1em auto 2em; padding: 0 1em; }
    h2 { text-align: center; margin: 0.4em 0 0.1em; }
    .sub { text-align: center; opacity: 0.75; font-size: 0.9em; margin: 0 0 1em; }
    .rings { display: flex; flex-wrap: wrap; gap: 0.5em; justify-content: center; margin-bottom: 1.2em; }
    .ring { display: flex; flex-direction: column; align-items: center; min-width: 6.5em; padding: 0.5em 0.7em; border: 1px solid rgba(212,175,55,0.55); border-radius: 10px; color: inherit; text-decoration: none; background: rgba(212,175,55,0.08); }
    .ring.mine { border-color: #27ae60; background: rgba(39,174,96,0.14); }
    .ring b { font-size: 1.5em; line-height: 1.1; }
    .cups { font-size: 0.85em; }
    .nm { font-size: 0.85em; font-weight: 700; }
    .wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.75; padding: 0.4em 0.6em; border-bottom: 2px solid rgba(127,127,127,0.4); }
    td { padding: 0.55em 0.6em; border-bottom: 1px solid rgba(127,127,127,0.22); vertical-align: top; text-align: left; }
    td.mine { background: rgba(39,174,96,0.14); }
    .yr { font-weight: 800; }
    .fin { white-space: nowrap; font-variant-numeric: tabular-nums; }
    .tn, .rc { display: block; font-size: 0.8em; opacity: 0.7; }
    .upset { display: inline-block; margin-top: 0.25em; font-size: 0.75em; font-weight: 700; color: #fff; background: #c0392b; border-radius: 999px; padding: 0.1em 0.6em; }
</style>
