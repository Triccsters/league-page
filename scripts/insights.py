"""insights.py - projected vs actual, and position-group surprises.

Called from extras.build_all(ctx). Writes src/lib/data/insights.json.

Projections come from Sleeper's own projection feed (the numbers managers
saw in the app), keyed on Sleeper player id, so no name matching. Sleeper
keeps past weeks, so every finished week can be graded after the fact.
That feed is not in Sleeper's public API docs: if it stops answering,
the page keeps the last good file and says how old it is.

Projected points are re-scored with the league's own scoring_settings,
so TE premium, 6-point passing TDs and the rest are counted the way the
league counts them. A starter with no projection counts as 0 and is
listed in "unprojected" so the gap is visible, not hidden.
"""
import os
import statistics
from collections import defaultdict

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
# kickers and defences swing too much week to week to call a surprise
GROUPS = ["QB", "RB", "WR", "TE"]
PROJ_URL = ("https://api.sleeper.app/projections/nfl/{season}/{week}?season_type=regular"
            + "".join(f"&position[]={p}" for p in POSITIONS))


def _get(url):
    import json, urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "league-page-updater"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _projections(season, week, cache_dir, read_json, write_json, final, shim_dir=None):
    """player_id -> projected stats for one week. A finished week is cached for good.

    A shimmed league (League Bound, on ESPN) uses ESPN's own projections,
    written by espn_extras.py as points already scored the league's way.
    They come back as {"__pts": n} so the scorer passes them straight through.
    """
    if shim_dir:
        pts = read_json(os.path.join(shim_dir, f"{week}.json"), None)
        if pts:
            return {pid: {"__pts": v} for pid, v in pts.items()}
    path = os.path.join(cache_dir, f"{season}-w{week:02d}.json")
    cached = read_json(path, None)
    if cached is not None:
        return cached
    rows = _get(PROJ_URL.format(season=season, week=week)) or []
    out = {r["player_id"]: r.get("stats") or {} for r in rows if r.get("player_id")}
    if final and out:
        write_json(path, out, compact=True)
    return out


def _scorer(scoring):
    rec = (scoring or {}).get("rec", 0) or 0
    fallback = "pts_ppr" if rec >= 1 else "pts_half_ppr" if rec >= 0.5 else "pts_std"

    def score(stats):
        if not stats:
            return None
        if "__pts" in stats:
            return round(stats["__pts"], 2)
        if scoring:
            v = sum((stats.get(k) or 0) * w for k, w in scoring.items())
            if v:
                return round(v, 2)
        v = stats.get(fallback)
        return round(v, 2) if v is not None else None
    return score


def build_insights(ctx):
    S, state, season = ctx["cur"], ctx["state"], ctx["season"]
    data, read_json, write_json = ctx["data"], ctx["read_json"], ctx["write_json"]
    out_path = os.path.join(data, "insights.json")
    weeks = [w for w in S.completed_weeks(state) if w < S.playoff_start]
    score = _scorer(S.league.get("scoring_settings"))
    # cached outside the repo: one file per week is ~3,000 players, too big to commit
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "league_page_projections")
    os.makedirs(cache_dir, exist_ok=True)
    repo = os.path.abspath(os.path.join(data, "..", "..", ".."))
    shim_dir = os.path.join(repo, "static", "shim", "v1", "projections")
    shim_dir = shim_dir if os.path.isdir(shim_dir) else None

    teams = {}
    pos_week = defaultdict(dict)          # handle -> week -> {pos: pts}
    players_week = []                      # per started player: proj vs actual
    feed_ok = True
    n_started = n_proj = n_pos = 0          # coverage, so a bad id map is reported, not drawn
    for w in weeks:
        try:
            proj = _projections(season, w, cache_dir, read_json, write_json, final=True, shim_dir=shim_dir)
        except Exception as e:             # feed down: keep the last good file
            print("insights: projections unavailable:", e)
            feed_ok = False
            break
        for m in S.matchups(w):
            h = S.handle.get(m.get("roster_id"))
            if not h:
                continue
            t = teams.setdefault(h, {"weeks": []})
            pp = m.get("players_points") or {}
            p_tot, a_tot, unproj, groups = 0.0, 0.0, [], defaultdict(float)
            for pid in m.get("starters") or []:
                if not pid or pid == "0":
                    continue
                info = dict(S.pinfo(pid))
                if pid.startswith("espn"):    # ESPN player Sleeper has no id for; pinfo calls it a DEF
                    info["pos"] = "?"
                act = round(pp.get(pid, 0) or 0, 2)
                pj = score(proj.get(pid))
                n_started += 1
                n_proj += pj is not None
                n_pos += info["pos"] in POSITIONS
                a_tot += act
                groups[info["pos"]] += act
                if pj is None:
                    unproj.append(info["name"])
                else:
                    p_tot += pj
                    players_week.append({"w": w, "h": h, "n": info["name"], "p": info["pos"],
                                         "proj": pj, "act": act, "d": round(act - pj, 2)})
            t["weeks"].append({"w": w, "proj": round(p_tot, 2), "act": round(a_tot, 2),
                               "d": round(a_tot - p_tot, 2), "unproj": unproj,
                               "pos": {k: round(v, 2) for k, v in groups.items()}})
            pos_week[h][w] = dict(groups)

    if not feed_ok:
        old = read_json(out_path, None)
        if old:
            old["stale"] = True
            write_json(out_path, old)
            return old

    for h, t in teams.items():
        ws = t["weeks"]
        t["name"] = h
        t["proj"] = round(sum(x["proj"] for x in ws), 2)
        t["act"] = round(sum(x["act"] for x in ws), 2)
        t["d"] = round(t["act"] - t["proj"], 2)
        t["beat"] = sum(1 for x in ws if x["d"] > 0)
        t["missed"] = sum(1 for x in ws if x["d"] < 0)

    # League Bound is ESPN, read through a shim: most of its player ids do not
    # map to Sleeper's, so its projections and positions would be fiction.
    proj_ok = n_started > 0 and n_proj / n_started >= 0.8
    pos_ok = n_started > 0 and n_pos / n_started >= 0.8
    if not proj_ok:
        for t in teams.values():
            for k in ("proj", "d", "beat", "missed"):
                t.pop(k, None)
            for x in t["weeks"]:
                for k in ("proj", "d", "unproj"):
                    x.pop(k, None)
        players_week = []
    surprises = _position_surprises(pos_week, weeks) if pos_ok else []
    latest = weeks[-1] if weeks else None
    lw = [p for p in players_week if p["w"] == latest]
    lw.sort(key=lambda p: p["d"])
    out = {
        "season": season, "through_week": latest, "stale": False,
        "projections": proj_ok, "positions": pos_ok,
        "coverage": round(n_proj / n_started, 3) if n_started else 0,
        "teams": sorted(teams.values(), key=lambda t: -t.get("d", t["act"])),
        "surprises": surprises,
        "week_best": list(reversed(lw[-8:])),
        "week_worst": lw[:8],
        "source": ("ESPN's own projections for this league" if shim_dir
                   else "Sleeper projections, re-scored with this league's scoring"),
    }
    write_json(out_path, out)
    return out


def _position_surprises(pos_week, weeks):
    """A group that has been weak (bottom third of the league at that position
    before this week) and suddenly beats both its own average and the league
    average by a clear margin, or a strong group that collapses."""
    out = []
    for i, w in enumerate(weeks):
        prior = weeks[:i]
        if len(prior) < 3:
            continue
        for pos in GROUPS:
            avgs = {}
            for h, by in pos_week.items():
                vals = [by[x].get(pos, 0) for x in prior if x in by]
                if vals:
                    avgs[h] = (statistics.mean(vals), statistics.pstdev(vals))
            if len(avgs) < 6:
                continue
            ranked = sorted(avgs, key=lambda h: avgs[h][0])
            third = max(1, len(ranked) // 3)
            weak, strong = set(ranked[:third]), set(ranked[-third:])
            league = statistics.mean(a for a, _ in avgs.values())
            if league <= 0:
                continue
            for h, by in pos_week.items():
                if w not in by or h not in avgs:
                    continue
                now, (mine, sd) = by[w].get(pos, 0), avgs[h]
                if h in weak and now >= max(mine + max(1.5 * sd, 6), league * 1.35):
                    kind = "breakout"
                elif h in strong and now <= min(mine - max(1.5 * sd, 6), league * 0.6):
                    kind = "collapse"
                else:
                    continue
                out.append({"w": w, "h": h, "pos": pos, "kind": kind, "pts": round(now, 2),
                            "avg": round(mine, 2), "league": round(league, 2),
                            "rank": ranked.index(h) + 1, "of": len(ranked)})
    out.sort(key=lambda s: (-s["w"], s["kind"], -abs(s["pts"] - s["avg"])))
    return out

# ---------------------------------------------------------------- trending
def build_trending(ctx, hours=168, limit=15):
    """Most-added and most-dropped players across all of Sleeper this past week,
    with who holds each one in this league. Sleeper asks for attribution."""
    S, data, write_json = ctx["cur"], ctx["data"], ctx["write_json"]
    shim = any(str(p).startswith("espn") for r in S.rosters for p in (r.get("players") or []))
    owner = {}
    if not shim:                  # League Bound's ids are ESPN's: can't say who holds whom
        for r in S.rosters:
            for p in r.get("players") or []:
                owner[p] = S.handle.get(r["roster_id"])
    out = {"hours": hours, "rostered_known": not shim}
    for kind in ("add", "drop"):
        rows = _get(f"https://api.sleeper.app/v1/players/nfl/trending/{kind}?lookback_hours={hours}&limit={limit}") or []
        lst = []
        for r in rows:
            pid = str(r.get("player_id"))
            info = S.pinfo(pid)
            lst.append({"n": info["name"], "p": info["pos"], "t": info.get("team"),
                        "c": r.get("count", 0), "h": owner.get(pid)})
        out[kind] = lst
    write_json(os.path.join(data, "trending.json"), out)
    return out