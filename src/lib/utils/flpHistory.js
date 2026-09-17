// Unified FL Players history (Yahoo 2014-2020 + Sleeper 2021-now).
// Data comes from scripts/update_site.py -> src/lib/data/history.json.
import history from '$lib/data/history.json';

export const managers = history.managers;
export const currentManagers = history.current;
export const generated = history.generated;

export const games = history.games.map(([season, week, era, a, pa, b, pb, playoff, label]) =>
    ({ season, week, era, a, pa, b, pb, playoff, label }));

export const nameOf = (handle) => managers[handle]?.name || handle;

export const slugFor = (x, y) => [x, y].sort((p, q) => p.localeCompare(q)).join('--');

export const pairFromSlug = (slug) => slug.split('--');

const eraLabel = (era) => (era === 'yahoo' ? 'Yahoo' : 'Sleeper');

// Everything about one pair of managers, from x's point of view.
export const rivalry = (x, y) => {
    const meetings = games
        .filter(g => (g.a === x && g.b === y) || (g.a === y && g.b === x))
        .map(g => {
            const xp = g.a === x ? g.pa : g.pb;
            const yp = g.a === x ? g.pb : g.pa;
            return {
                season: g.season, week: g.week, era: g.era, eraLabel: eraLabel(g.era),
                playoff: g.playoff, label: g.label, xp, yp,
                winner: xp > yp ? x : yp > xp ? y : null,
                margin: Math.round(Math.abs(xp - yp) * 100) / 100,
            };
        });

    const tally = (list) => ({
        x: list.filter(m => m.winner === x).length,
        y: list.filter(m => m.winner === y).length,
        t: list.filter(m => !m.winner).length,
        xpts: Math.round(list.reduce((s, m) => s + m.xp, 0) * 100) / 100,
        ypts: Math.round(list.reduce((s, m) => s + m.yp, 0) * 100) / 100,
    });

    // Current streak, newest first.
    let streak = null;
    for (const m of [...meetings].reverse()) {
        if (!m.winner) break;
        if (!streak) streak = { who: m.winner, n: 1 };
        else if (m.winner === streak.who) streak.n++;
        else break;
    }

    // Running win count for the chart.
    let rx = 0, ry = 0;
    const running = meetings.map(m => {
        if (m.winner === x) rx++;
        if (m.winner === y) ry++;
        return { x: rx, y: ry };
    });

    const decided = meetings.filter(m => m.winner);
    const closest = [...decided].sort((p, q) => p.margin - q.margin)[0] || null;
    const biggest = [...decided].sort((p, q) => q.margin - p.margin)[0] || null;
    const finals = meetings.filter(m => m.label === 'Championship');

    return {
        x, y, meetings, running, streak, closest, biggest, finals,
        all: tally(meetings),
        regular: tally(meetings.filter(m => !m.playoff)),
        playoffs: tally(meetings.filter(m => m.playoff)),
        yahoo: tally(meetings.filter(m => m.era === 'yahoo')),
        sleeper: tally(meetings.filter(m => m.era !== 'yahoo')),
    };
};

// Every pair among the current managers, for the index page.
export const currentPairs = () => {
    const out = [];
    const list = [...currentManagers].sort((p, q) => nameOf(p).localeCompare(nameOf(q)));
    for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
            const r = rivalry(list[i], list[j]);
            out.push({
                slug: slugFor(list[i], list[j]),
                x: list[i], y: list[j],
                all: r.all, streak: r.streak,
                games: r.meetings.length,
                finals: r.finals.length,
            });
        }
    }
    return out;
};
