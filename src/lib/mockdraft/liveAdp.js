// Live ADP for the mock draft, read in the visitor's browser straight from
// Sleeper (its API allows cross-origin reads, checked 2026-10-13). The baked
// board in static/data/mock_draft.json supplies byes and each player's measured
// ADP spread (from Fantasy Football Calculator); this replaces the ADP itself
// with Sleeper's current number, and follows Sleeper into the next season on
// its own. If Sleeper is unreachable or has no ADP yet, the snapshot stands.

const API = 'https://api.sleeper.app';
const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
const FIELD = { 'half-ppr': 'adp_half_ppr', ppr: 'adp_ppr', standard: 'adp_std', '2qb': 'adp_2qb' };
const FALLBACK = ['adp_half_ppr', 'adp_ppr', 'adp_std', 'adp_2qb', 'adp_dynasty_half_ppr'];
const MIN_RANKED = 150; // fewer than this and the season's ADP is not out yet

const read = (s, f) => (s && s[f] != null && s[f] < 900 ? s[f] : null);
const nameKey = (name, pos) => `${String(name).toLowerCase().replace(/[^a-z]/g, '')}|${pos}`;

async function seasonRows(season) {
    const all = [];
    for (const pos of POSITIONS) {
        const url = `${API}/projections/nfl/${season}?season_type=regular&position%5B%5D=${pos}&order_by=pts_half_ppr`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Sleeper ${res.status}`);
        all.push(...(await res.json()));
    }
    return all;
}

/**
 * @returns {Promise<{players: object[], season: string, ranked: number} | null>}
 */
export async function liveBoard(snapshotPlayers, scoring) {
    const field = FIELD[scoring] || 'adp_half_ppr';
    const order = [field, ...FALLBACK.filter((f) => f !== field)];
    let state;
    try { state = await fetch(`${API}/v1/state/nfl`).then((r) => r.json()); } catch { return null; }
    const seasons = [...new Set([state?.league_season, state?.season].filter(Boolean))];

    for (const season of seasons) {
        let rows;
        try { rows = await seasonRows(season); } catch { continue; }
        const live = new Map();
        for (const rec of rows) {
            const s = rec.stats || {};
            let adp = null;
            for (const f of order) { adp = read(s, f); if (adp != null) break; }
            if (adp == null) continue;
            const p = rec.player || {};
            const prior = live.get(String(rec.player_id));
            if (prior && prior.adp <= adp) continue;
            live.set(String(rec.player_id), {
                adp, primary: read(s, field) != null,
                name: `${p.first_name || ''} ${p.last_name || ''}`.trim(), position: p.position,
                team: rec.team || p.team || null, points: s.pts_half_ppr ?? null,
            });
        }
        const ranked = [...live.values()].filter((l) => l.primary).length;
        if (ranked < MIN_RANKED) continue;

        const byName = new Map(snapshotPlayers.map((p) => [nameKey(p.name, p.position), p]));
        const used = new Set();
        const out = [];
        for (const [id, l] of live) {
            const base = snapshotPlayers.find((p) => p.id === id) || byName.get(nameKey(l.name, l.position));
            if (base) {
                used.add(base.id);
                out.push({ ...base, adp: l.adp, sleeperAdp: l.adp, team: l.team || base.team });
            } else if (l.primary && POSITIONS.includes(l.position)) {
                // A player the snapshot never had (a rookie next year, say). No
                // measured spread, so it is estimated from where he goes.
                out.push({
                    id, key: id, name: l.name, position: l.position, team: l.team, bye: null,
                    adp: l.adp, adpRank: 0, adpStdev: Math.max(1.5, l.adp * 0.12), stdevMeasured: false,
                    points: l.points, sleeperAdp: l.adp, ffcAdp: null, injuryStatus: null,
                    adpBorrowedFrom: null, timesDrafted: 0, sources: ['sleeper'],
                });
            }
        }
        // Snapshot players Sleeper no longer ranks go to the back of the board.
        const tail = Math.max(...out.map((p) => p.adp)) + 1;
        for (const p of snapshotPlayers) if (!used.has(p.id)) out.push({ ...p, adp: tail + p.adp });
        out.sort((a, b) => a.adp - b.adp);
        out.forEach((p, i) => { p.adpRank = i + 1; });
        return { players: out, season: String(season), ranked };
    }
    return null;
}
