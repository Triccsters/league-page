<script>
    // Requests and issues, and the open call to put names to the old teams.
    // The list is computed from history.json, so it shrinks as managers are named.
    import { games, managers, teamName, site } from '$lib/utils/flpHistory';

    export let contact = 'T.J.';
    export let where = 'the league chat on Sleeper';

    // every manager Yahoo never named, with the teams and seasons they played
    const unknown = (() => {
        const seasons = {};
        for (const g of games) {
            for (const h of [g.a, g.b]) {
                if (managers[h]?.hidden) (seasons[h] ||= new Set()).add(g.season);
            }
        }
        return Object.entries(seasons)
            .map(([h, set]) => {
                const yrs = [...set].sort();
                const names = [...new Set(yrs.map(y => teamName(y, h)).filter(Boolean))];
                return { h, yrs, names: names.length ? names : [h.replace(/^\?/, '')] };
            })
            .sort((a, b) => a.yrs[0] - b.yrs[0] || a.names[0].localeCompare(b.names[0]));
    })();

    const span = (yrs) => (yrs.length === 1 ? `${yrs[0]}` : `${yrs[0]}–${yrs[yrs.length - 1]}`);
</script>

<section class="hw">
    <h3>Requests, problems, and a favor</h3>
    <p>
        Something wrong on the site, a number that looks off, or a page you want built? Tell {contact}
        in {where}. It gets fixed.
    </p>

    {#if unknown.length}
        <p class="ask">
            <b>The favor:</b> {unknown.length} teams from the Yahoo years are still on the site without a
            name attached. Yahoo hid the manager and the accounts are long gone, so the only way to put a
            person to these is if somebody remembers. Recognize one? Say so and it gets fixed everywhere,
            back to {site.first_season}.
        </p>
        <ul>
            {#each unknown as u}
                <li><b>{u.names.join(' / ')}</b> <small>{span(u.yrs)}</small></li>
            {/each}
        </ul>
    {/if}
</section>

<style>
    .hw { max-width: 900px; margin: 2em auto 1em; padding: 0.9em 1.1em; text-align: left;
          border: 1px solid rgba(127,127,127,0.28); border-radius: 10px; }
    h3 { margin: 0 0 0.4em; font-size: 1em; }
    p { margin: 0 0 0.6em; font-size: 0.9em; line-height: 1.5; }
    .ask { opacity: 0.95; }
    ul { list-style: none; margin: 0.2em 0 0; padding: 0;
         display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 0.25em 0.8em; }
    li { font-size: 0.86em; padding: 0.15em 0; border-bottom: 1px solid rgba(127,127,127,0.14); }
    li small { opacity: 0.6; margin-left: 0.35em; }
</style>
