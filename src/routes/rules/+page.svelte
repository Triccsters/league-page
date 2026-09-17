<script>
    import rules from '$lib/data/rules.json';
    import extra from '$lib/data/rules_extra.json';
    import { site } from '$lib/utils/flpHistory';

    const groups = [
        ['Defense and special teams', /defense|def\/st|allowed|^sack$|^interception$|forced|safety|blocked|stop|3 and out|punt|tackle|qb hit|defended|defensive|special|return|^fumble recovery$/i],
        ['Passing', /pass|completion|sacked|interception thrown|pick-six/i],
        ['Rushing', /rush|carries/i],
        ['Receiving', /reception|receiving/i],
        ['Kicking', /FG|extra point/i],
        ['Other', /./],
    ];
    const order = ['Passing', 'Rushing', 'Receiving', 'Kicking', 'Defense and special teams', 'Other'];
    const scoring = {};
    for (const s of rules.scoring) {
        const g = groups.find(([, re]) => re.test(s.name))[0];
        (scoring[g] ||= []).push(s);
    }
    const fmt = (v) => (v > 0 ? '+' : '') + v;
    const changeSeasons = [
        ...rules.history.filter(h => h.changes.length).map(h => ({ ...h, changes: [...h.changes] })),
    ];
    for (const c of extra.changes || []) {
        let s = changeSeasons.find(x => x.season === c.season);
        if (!s) changeSeasons.push(s = { season: c.season, changes: [] });
        s.changes.push({ area: 'Commissioner note', what: c.text });
    }
    changeSeasons.sort((a, b) => b.season - a.season);
</script>

<svelte:head><title>League Rules | {site.league_name}</title></svelte:head>

<div class="holder">
    <h1>League Rules</h1>
    <p class="sub">The {rules.season} rules, read straight from Sleeper, plus every rule change since {rules.first_sleeper_season}.</p>

    <div class="cols">
        <section>
            <h2>League settings</h2>
            <table><tbody>
                {#each rules.settings as s}<tr><td>{s.name}</td><td><b>{s.value}</b></td></tr>{/each}
            </tbody></table>
        </section>
        <section>
            <h2>Starting lineup</h2>
            <table><tbody>
                {#each rules.lineup as p}<tr><td>{p.name}</td><td><b>{p.count}</b></td></tr>{/each}
            </tbody></table>
        </section>
    </div>

    {#if extra.rules?.length}
        <h2>League rules</h2>
        {#each extra.rules as r}
            <div class="rule"><b>{r.title}</b><p>{r.text}</p></div>
        {/each}
    {/if}

    <h2>Scoring</h2>
    <div class="cols three">
        {#each order.filter(g => scoring[g]) as g}
            <section>
                <h3>{g}</h3>
                <table><tbody>
                    {#each scoring[g] as s}<tr><td>{s.name}</td><td class="num" class:neg={s.points < 0}>{fmt(s.points)}</td></tr>{/each}
                </tbody></table>
            </section>
        {/each}
    </div>

    <h2>Rule changes</h2>
    {#if changeSeasons.length === 0}
        <p class="sub">No settings have changed since {rules.first_sleeper_season}.</p>
    {/if}
    {#each changeSeasons as h}
        <section class="season">
            <h3>{h.season}</h3>
            <ul>
                {#each h.changes as c}
                    <li><span class="area">{c.area}</span> {c.what}{#if c.from !== undefined}: <s>{c.from}</s> → <b>{c.to}</b>{/if}</li>
                {/each}
            </ul>
        </section>
    {/each}
    <p class="stamp">Changes are found by comparing each season's Sleeper settings with the season before. Scoring values are points per unit (per yard for yardage).</p>
</div>

<style>
    .holder { max-width: 960px; margin: 0 auto; padding: 1.5em 1em; }
    h1 { text-align: center; margin-bottom: 0.2em; }
    .sub, .stamp { text-align: center; opacity: 0.75; }
    .stamp { font-size: 0.85em; margin-top: 2em; }
    h2 { margin-top: 1.6em; border-bottom: 2px solid rgba(127,127,127,0.3); padding-bottom: 0.2em; font-size: 1.2em; }
    h3 { margin: 0.6em 0 0.2em; font-size: 1em; }
    .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0 2em; }
    .cols.three { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
    table { width: 100%; border-collapse: collapse; }
    td { padding: 0.35em 0.4em; border-bottom: 1px solid rgba(127,127,127,0.2); font-size: 0.92em; }
    .num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; color: #2ecc71; }
    .num.neg { color: #e74c3c; }
    .rule { border-left: 4px solid #3498db; padding: 0.3em 0.8em; margin: 0.6em 0; }
    .rule p { margin: 0.2em 0 0; }
    .season { border: 1px solid rgba(127,127,127,0.3); border-radius: 8px; padding: 0.5em 1em; margin: 0.8em 0; }
    ul { margin: 0.3em 0; padding-left: 1.2em; }
    li { margin: 0.2em 0; }
    .area { display: inline-block; font-size: 0.72em; font-weight: 700; text-transform: uppercase; background: #34495e; color: #fff; border-radius: 3px; padding: 0.05em 0.4em; margin-right: 0.3em; }
    s { opacity: 0.6; }
</style>
