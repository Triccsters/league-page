<script>
    // The running story of one rivalry, written from the numbers (T.J., 2026-11-15):
    // where the series stands, how it got there, and what the next meeting means.
    // Nothing here is typed in. It reads history.json and odds.json, which the build
    // refreshes every day, so the story moves on by itself after every game.
    import { rivalry, nameOf, site, currentManagers } from '$lib/utils/flpHistory';
    import odds from '$lib/data/odds.json';

    export let x;
    export let y;

    const r1 = (v) => Math.round(v * 10) / 10;
    const pct = (v) => (v >= 99.95 ? '100%' : v < 0.05 ? 'under 0.1%' : `${r1(v)}%`);
    const MARKS = new Set([5, 10, 15, 20, 25, 30, 40, 50]);
    const REAL = new Set(['Quarterfinal', 'Semifinal', 'Championship']);
    const ord = (n) => `${n}${n % 100 >= 11 && n % 100 <= 13 ? 'th' : ['th', 'st', 'nd', 'rd'][n % 10] || 'th'}`;

    $: r = rivalry(x, y);
    $: X = nameOf(x);
    $: Y = nameOf(y);
    $: story = (() => {
        const ms = r.meetings, n = ms.length;
        if (!n) return null;
        const past = [], now = [];
        const lead = r.all.x === r.all.y ? null : r.all.x > r.all.y ? x : y;
        const hi = Math.max(r.all.x, r.all.y), lo = Math.min(r.all.x, r.all.y);
        const ties = r.all.t ? `, with ${r.all.t} tie${r.all.t > 1 ? 's' : ''}` : '';
        past.push(lead
            ? `${nameOf(lead)} leads the series ${hi}-${lo}${ties} across ${n} meeting${n > 1 ? 's' : ''} since ${ms[0].season}.`
            : `The series is level at ${hi}-${lo}${ties} after ${n} meeting${n > 1 ? 's' : ''} since ${ms[0].season}.`);

        // did it change hands? compare the first half with the second
        if (n >= 8) {
            const half = Math.floor(n / 2);
            const w = (list, h) => list.filter((m) => m.winner === h).length;
            const a = ms.slice(0, half), b = ms.slice(half);
            const la = w(a, x) - w(a, y), lb = w(b, x) - w(b, y);
            if (la * lb < 0) {
                const early = la > 0 ? x : y, late = lb > 0 ? x : y;
                past.push(`It has changed hands. ${nameOf(early)} went ${Math.max(w(a, x), w(a, y))}-${Math.min(w(a, x), w(a, y))} through ${a[a.length - 1].season}; since then ${nameOf(late)} is ${Math.max(w(b, x), w(b, y))}-${Math.min(w(b, x), w(b, y))}.`);
            }
        }
        if (n >= 5) {
            const last = ms.slice(-5), wx = last.filter((m) => m.winner === x).length, wy = last.filter((m) => m.winner === y).length;
            if (wx !== wy) past.push(`${nameOf(wx > wy ? x : y)} has taken ${Math.max(wx, wy)} of the last 5.`);
            else past.push('The last 5 are split.');
        }
        const dec = ms.filter((m) => m.winner);
        if (dec.length >= 4) {
            const close = dec.filter((m) => m.margin < 10).length;
            const avg = r1(dec.reduce((s, m) => s + m.margin, 0) / dec.length);
            past.push(`The average margin is ${avg} points${close ? `, and ${close} of the ${dec.length} were decided by fewer than 10` : ''}.`);
        }
        const po = ms.filter((m) => m.playoff && REAL.has(m.label));
        if (po.length) {
            const px = po.filter((m) => m.winner === x).length, py = po.filter((m) => m.winner === y).length;
            past.push(`In the playoffs they have met ${po.length === 1 ? 'once' : `${po.length} times`}${px === py ? `, ${px}-${py}` : `, ${nameOf(px > py ? x : y)} ahead ${Math.max(px, py)}-${Math.min(px, py)}`}.`);
        }

        // this season
        const both = currentManagers.includes(x) && currentManagers.includes(y);
        const season = odds?.season === site.season ? odds : null;
        const tx = season?.teams?.find((t) => t.h === x), ty = season?.teams?.find((t) => t.h === y);
        let next = null;
        if (both && season?.schedule) {
            for (const wk of Object.keys(season.schedule).map(Number).sort((a, b) => a - b)) {
                if (season.schedule[wk].some(([a, b]) => (a === x && b === y) || (a === y && b === x))) { next = wk; break; }
            }
        }
        if (both) {
            const met = ms.filter((m) => m.season === site.season);
            if (met.length) {
                now.push(met.map((m) => `${m.winner ? nameOf(m.winner) : 'Nobody'} won ${m.label || `week ${m.week}`} ${Math.max(m.xp, m.yp)} to ${Math.min(m.xp, m.yp)}`).join('. ') + ` in ${site.season}.`);
            }
            if (tx && ty) now.push(`${X} is ${tx.w}-${tx.l} with a ${pct(tx.playoff)} chance at the playoffs; ${Y} is ${ty.w}-${ty.l} at ${pct(ty.playoff)}.`);
            if (next) {
                const stakes = [];
                for (const [h, mine, theirs] of [[x, r.all.x, r.all.y], [y, r.all.y, r.all.x]]) {
                    const bits = [];
                    if (MARKS.has(mine + 1)) bits.push(`a ${ord(mine + 1)} win in the series`);
                    if (mine + 1 === theirs) bits.push('a level series');
                    else if (mine === theirs) bits.push('the series lead');
                    if (r.streak && r.streak.who === h && r.streak.n >= 2) bits.push(`${r.streak.n + 1} in a row`);
                    else if (r.streak && r.streak.who !== h && r.streak.n >= 3) bits.push(`an end to a run of ${r.streak.n} losses`);
                    if (bits.length) stakes.push(`A win gives ${nameOf(h)} ${bits.join(' and ')}.`);
                }
                now.push(`They meet in week ${next}.` + (stakes.length ? ' ' + stakes.join(' ') : ''));
            } else if (season) {
                now.push(`There is no regular-season meeting left this year, so the playoffs are the only way they play again.`);
            }
        } else {
            const gone = !currentManagers.includes(x) ? X : Y;
            now.push(`${gone} is no longer in the league, so the series stands where it is. The last meeting was ${ms[n - 1].season} ${ms[n - 1].label || `week ${ms[n - 1].week}`}.`);
        }
        return { past, now, both };
    })();
</script>

{#if story}
    <section class="ro">
        <p class="eyebrow">Outlook</p>
        <h3>The story so far</h3>
        <p>{story.past.join(' ')}</p>
        <h3>{story.both ? `Where it stands in ${site.season}` : 'Where it stands'}</h3>
        <p>{story.now.join(' ')}</p>
        <p class="foot">Written from the results and the playoff odds, and updated after every game.</p>
    </section>
{/if}

<style>
    .ro { text-align: left; background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-radius: 12px; padding: 0.9em 1.1em; margin: 1.2em 0; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    h3 { margin: 0.5em 0 0.2em; font-size: 1em; color: #ffffff; }
    p { margin: 0; font-size: 0.93em; line-height: 1.55; color: #d5dceb; }
    .foot { margin-top: 0.7em; font-size: 0.78em; color: #aab6cc; }
</style>
