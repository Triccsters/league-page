"""power.py - power rankings built at the Tuesday update, not in the browser.

Writes src/lib/data/power.json. Three measures, each ranked, then blended:

  rest of season  Every remaining regular-season week, each roster's best
                  legal lineup on that week's Sleeper projections, scored with
                  this league's own scoring (TE premium, 6-point passing TDs and
                  the rest). Byes count, because a bye projects to zero.
  scoring now     Points per game this season.
  all-play        This season's record if every team played every other team
                  every week. Takes the schedule out of it.

Blend: 50% rest of season, 30% scoring now, 20% all-play, as z-scores. Early
in the year the rest of the season is most of what is left to play, so it
carries the most weight.

Dynasty leagues also get a dynasty roster value from the FantasyPros dynasty
ranks already in ecr.json. It is shown next to the power ranking, not blended
into it: who wins this year and who owns the future are different questions.
"""
import os
import statistics
from collections import defaultdict

ELIG = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"}, "K": {"K"},
        "DEF": {"DEF"}, "FLEX": {"RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"},
        "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
WEIGHTS = {"ros": 0.5, "ppg": 0.3, "allplay": 0.2}
# how deep each position runs before a dynasty rank is worth nothing
DEPTH = {"QB": 32, "RB": 60, "WR": 72, "TE": 28}


def _best_lineup(slots, players, pts, pos_of):
    order = sorted(slots, key=lambda s: len(ELIG.get(s, ())))
    used, total = set(), 0.0
    for s in order:
        best = None
        for p in players:
            if p in used or pos_of(p) not in ELIG.get(s, ()):
                continue
            if best is None or pts.get(p, 0) > pts.get(best, 0):
                best = p
        if best:
            used.add(best)
            total += pts.get(best, 0)
    return total


def _z(vals):
    m = statistics.mean(vals.values())
    sd = statistics.pstdev(vals.values()) or 1
    return {k: (v - m) / sd for k, v in vals.items()}


def _ranks(vals, reverse=True):
    order = sorted(vals, key=lambda k: vals[k], reverse=reverse)
    return {k: i + 1 for i, k in enumerate(order)}


def build_power(ctx):
    import insights as I
    S, state, season = ctx["cur"], ctx["state"], ctx["season"]
    data, read_json, write_json = ctx["data"], ctx["read_json"], ctx["write_json"]
    out_path = os.path.join(data, "power.json")
    done = [w for w in S.completed_weeks(state) if w < S.playoff_start]
    last = (done[-1] if done else 0)
    left = list(range(last + 1, S.playoff_start))
    score = I._scorer(S.league.get("scoring_settings"))
    slots = [s for s in (S.league.get("roster_positions") or []) if s in ELIG]
    pos_of = lambda pid: S.pinfo(pid)["pos"]
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "league_page_projections")

    rosters = {S.handle.get(r["roster_id"]): [p for p in (r.get("players") or []) if p]
               for r in S.rosters if S.handle.get(r["roster_id"])}

    # 1. rest of season, on projections
    ros = defaultdict(float)
    weeks_used = 0
    for w in left:
        try:
            proj = I._projections(season, w, cache_dir, read_json, write_json, final=False)
        except Exception as e:
            print("power: projections unavailable for week", w, e)
            continue
        if not proj:
            continue
        weeks_used += 1
        for h, players in rosters.items():
            pts = {p: (score(proj.get(p)) or 0) for p in players}
            ros[h] += _best_lineup(slots, players, pts, pos_of)
    ros_pg = {h: round(ros[h] / weeks_used, 2) if weeks_used else 0 for h in rosters}

    # 2 and 3. scoring and all-play, this season's regular season
    pf, games = defaultdict(float), defaultdict(int)
    ap_w, ap_g = defaultdict(float), defaultdict(int)
    for w in done:
        week_scores = {}
        for m in S.matchups(w):
            h = S.handle.get(m.get("roster_id"))
            if h and m.get("matchup_id") is not None:
                week_scores[h] = m.get("points") or 0
        for h, p in week_scores.items():
            pf[h] += p
            games[h] += 1
            others = [q for k, q in week_scores.items() if k != h]
            ap_w[h] += sum(1 for q in others if p > q) + 0.5 * sum(1 for q in others if p == q)
            ap_g[h] += len(others)
    ppg = {h: round(pf[h] / games[h], 2) if games[h] else 0 for h in rosters}
    allplay = {h: round(ap_w[h] / ap_g[h], 3) if ap_g[h] else 0 for h in rosters}

    measures = {"ros": ros_pg, "ppg": ppg, "allplay": allplay}
    if not weeks_used:                        # season over or feed down: blend the rest
        measures.pop("ros")
    w_total = sum(WEIGHTS[k] for k in measures)
    zs = {k: _z(v) for k, v in measures.items()}
    blend = {h: sum(WEIGHTS[k] / w_total * zs[k][h] for k in measures) for h in rosters}
    rank = _ranks(blend)

    # dynasty value, from the same FantasyPros dynasty ranks the roster pages use
    dyn = {}
    if ctx.get("dynasty"):
        import rosters as R
        from extras import pkey
        ecr = R._load_ecr(ctx)
        for h, players in rosters.items():
            v = 0.0
            for p in players:
                info = S.pinfo(p)
                r = ecr["map"].get((info["pos"], pkey(info["name"])))
                d = DEPTH.get(info["pos"])
                if r and d:
                    v += max(0.0, 1 - (r - 1) / d)
            dyn[h] = round(v, 2)
    dyn_rank = _ranks(dyn) if dyn else {}

    old = read_json(out_path, None) or {}
    prev = old.get("prev_rank", {}) if old.get("through_week") == last else \
        {t["h"]: t["rank"] for t in old.get("teams", [])}
    teams = []
    for h in rosters:
        t = {"h": h, "rank": rank[h], "score": round(blend[h], 3),
             "ros": ros_pg[h], "ppg": ppg[h], "allplay": allplay[h],
             "ros_rank": _ranks(ros_pg)[h], "ppg_rank": _ranks(ppg)[h],
             "allplay_rank": _ranks(allplay)[h], "prev": prev.get(h)}
        if dyn:
            t["dyn"], t["dyn_rank"] = dyn[h], dyn_rank[h]
        teams.append(t)
    teams.sort(key=lambda t: t["rank"])
    doc = {"season": season, "through_week": last, "weeks_left": weeks_used,
           "first_left": left[0] if left else None, "last_left": left[-1] if left else None,
           "weights": {k: WEIGHTS[k] for k in measures}, "dynasty": bool(dyn),
           "dyn_asof": (R._load_ecr(ctx).get("asof") if dyn else None),
           "prev_rank": prev, "teams": teams,
           "source": "Sleeper weekly projections scored with this league's scoring",
           # local date of this build: the home page says "as of" this, since the board
           # moves daily with projections while a newsletter issue is a snapshot
           "generated": __import__("datetime").date.today().isoformat()}
    write_json(out_path, doc)
    return doc
