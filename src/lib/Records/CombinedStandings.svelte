<script>
    // All-time table for every manager, Yahoo 2014-2020 and Sleeper 2021-now joined.
    import { games, nameOf, managers, generated } from '$lib/utils/flpHistory';

    const REAL = new Set(['Quarterfinal', 'Semifinal', 'Championship']);
    const rows = {};
    const row = (h) => (rows[h] ||= { h, seasons: new Set(), w: 0, l: 0, t: 0, pf: 0, pa: 0, g: 0,
        pw: 0, pl: 0, titles: [], finals: 0, yahoo: [0, 0], sleeper: [0, 0] });

    for (const g of games) {
        for (const [me, mp, op] of [[g.a, g.pa, g.pb], [g.b, g.pb, g.pa]]) {
            const r = row(me);
            r.seasons.add(g.season);
            const won = mp > op, lost = mp < op;
            if (!g.playoff) {
                r.g++; r.pf += mp; r.pa += op;
                if (won) r.w++; else if (lost) r.l++; else r.t++;
                const era = g.era === 'yahoo' ? r.yahoo : r.sleeper;
                if (won) era[0]++; else if (lost) era[1]++;
            } else if (REAL.has(g.label)) {
                if (won) r.pw++; else if (lost) r.pl++;
                if (g.label === 'Championship') {
                    r.finals++;
                    if (won) r.titles.push(g.season);
                }
            }
        }
    }

    const list = Object.values(rows)
        .map(r => ({ ...r, pct: r.g ? (r.w + r.t / 2) / r.g : 0, avg: r.g ? r.pf / r.g : 0 }))
        .sort((a, b) => b.titles.length - a.titles.length || b.pct - a.pct);
    const pct = (x) => (x * 100).toFixed(1) + '%';
    const first = Math.min(...games.map(g => g.season));
    const last = Math.max(...games.map(g => g.season));
</script>

<h2>🏈 All-time, every era ({first}–{last})</h2>
<p class="note">One row per person across both platforms. Regular season only in W-L; playoff record counts real playoff rounds, not consolation games.</p>
<div class="scroll">
<table>
    <thead>
        <tr><th>#</th><th>Manager</th><th>Seasons</th><th>W-L-T</th><th>Win %</th><th>Yahoo</th><th>Sleeper</th><th class="num">PF/game</th><th>Playoffs</th><th>🏆</th><th>Finals</th></tr>
    </thead>
    <tbody>
        {#each list as r, i}
            <tr>
                <td>{i + 1}</td>
                <td><b>{nameOf(r.h)}</b>{#if managers[r.h]?.yahoo && managers[r.h].yahoo !== nameOf(r.h)} <small>({managers[r.h].yahoo} on Yahoo)</small>{/if}</td>
                <td>{r.seasons.size}</td>
                <td>{r.w}-{r.l}{r.t ? `-${r.t}` : ''}</td>
                <td>{pct(r.pct)}</td>
                <td>{r.yahoo[0] + r.yahoo[1] ? `${r.yahoo[0]}-${r.yahoo[1]}` : '—'}</td>
                <td>{r.sleeper[0] + r.sleeper[1] ? `${r.sleeper[0]}-${r.sleeper[1]}` : '—'}</td>
                <td class="num">{r.avg.toFixed(1)}</td>
                <td>{r.pw}-{r.pl}</td>
                <td>{r.titles.length ? `${r.titles.length} (${r.titles.join(', ')})` : '—'}</td>
                <td>{r.finals}</td>
            </tr>
        {/each}
    </tbody>
</table>
</div>
<p class="note">Data updated {generated.slice(0, 10)}. The tables below are the original per-platform views.</p>

<style>
    .note { opacity: 0.7; font-size: 0.9em; }
    .scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.45em 0.5em; border-bottom: 1px solid rgba(127,127,127,0.25); text-align: left; font-size: 0.92em; white-space: nowrap; }
    .num { text-align: right; }
    small { opacity: 0.6; }
</style>
