// Pictures for managers, players and NFL teams (T.J., 2026-10-14).
// Team avatar = the team's picture in this league (Sleeper team photo or ESPN
// logo), falling back to the manager's own photo. Built into managers.json.
import managers from '$lib/data/managers.json';

const byHandle = Object.fromEntries((managers || []).map((m) => [m.handle, m]));

export const avatarOf = (h) => {
    const m = byHandle[h];
    const a = m?.avatar || m?.photo;
    return a && !a.includes('question.jpg') ? a : null;
};

export const teamLogo = (t) => (t ? `https://sleepercdn.com/images/team_logos/nfl/${String(t).toLowerCase()}.png` : null);

// p: {id, pos, nfl}. Defenses get their team logo, everyone else a headshot.
export const playerImg = (p) => {
    if (!p || p.id == null) return null;
    const id = String(p.id);
    if (p.pos === 'DEF' || /^[A-Z]{2,3}$/.test(id)) return teamLogo(p.nfl || id);
    return /^\d+$/.test(id) ? `https://sleepercdn.com/content/nfl/players/thumb/${id}.jpg` : null;
};

// a picture that fails to load just disappears instead of showing a broken icon
export const hideBroken = (e) => { e.currentTarget.style.display = 'none'; };
