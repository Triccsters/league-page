"""Waiver returns and league awards, computed from the same data the other pages use.

Definitions, repeated on the pages:
  Waiver value  Points a player scored WHILE STARTED for the manager who picked
                him up, that season. Players that manager drafted that season
                don't count, so this is only what the waiver wire added.
  Awards        One winner per category, with the next two listed. A manager
                needs 3 seasons to win a rate-based award (win %, consistency).
"""
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

REAL = {"Quarterfinal", "Semifinal", "Championship"}
MIN_SEASONS = 3


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- waivers
def build_waivers(ctx, rows, picks):
    from extras import pkey, started_index
    idx = started_index(rows)
    drafted = {(p[0], p[3], pkey(p[4])) for p in picks}     # season, manager, player
    adds = []                                               # season, manager, player, faab, era
    if ctx["mode"] == "vault":
        import flp
        for t in flp.txns():
            if t.kind == "add" and t.season < ctx["season"]:
                adds.append((t.season, t.manager, flp.norm_player(t.player), t.faab, t.era))
    for S in ctx["live_seasons"]:
        if ctx["mode"] == "vault" and S.season != ctx["season"]:
            continue
        for leg in range(0, 19):
            try:
                txs = ctx["sleeper"](f"/league/{S.league_id}/transactions/{leg}") or []
            except Exception:
                continue
            for tx in txs:
                if tx.get("type") not in ("waiver", "free_agent") or tx.get("status") != "complete":
                    continue
                bid = ((tx.get("settings") or {}).get("waiver_bid"))
                for pid, rid in (tx.get("adds") or {}).items():
                    h = S.handle.get(rid)
                    if not h:
                        continue
                    adds.append((S.season, h, S.pinfo(pid)["name"], bid, "sleeper"))
    seen, pickups = set(), []
    for season, h, name, faab, era in adds:
        k = pkey(name)
        if (season, h, k) in drafted or (season, h, k) in seen:
            continue
        seen.add((season, h, k))
        pts, starts = 0.0, 0
        for s, w, p in idx.get((h, k), ()):
            if s == season:
                pts += p
                starts += 1
        pickups.append({"season": season, "h": h, "n": name, "faab": faab, "era": era,
                        "pts": round(pts, 2), "st": starts})
    per = defaultdict(lambda: {"adds": 0, "pts": 0.0, "faab": 0, "bids": 0, "hits": 0})
    for p in pickups:
        e = per[p["h"]]
        e["adds"] += 1
        e["pts"] += p["pts"]
        e["hits"] += p["pts"] >= 50
        if p["faab"]:
            e["faab"] += p["faab"]
            e["bids"] += 1
    managers = {h: {"adds": e["adds"], "pts": round(e["pts"], 1), "faab": e["faab"], "bids": e["bids"],
                    "hits": e["hits"], "per_add": round(e["pts"] / max(1, e["adds"]), 1),
                    "per_dollar": round(e["pts"] / e["faab"], 2) if e["faab"] >= 50 else None}
                for h, e in per.items()}
    pickups.sort(key=lambda p: -p["pts"])
    data = {"generated": now(), "pickups": pickups[:150], "count": len(pickups), "managers": managers,
            "first_season": min((p["season"] for p in pickups), default=None),
            "faab_from": min((p["season"] for p in pickups if p["faab"]), default=None)}
    ctx["write_json"](os.path.join(ctx["static"], "waivers.json"), data, compact=True)
    return data


# ---------------------------------------------------------------- awards
def _season_tables(games, season_filter=None):
    """Per (season, manager): record, points, week scores, playoff and finish info."""
    t = defaultdict(lambda: {"w": 0, "l": 0, "pf": 0.0, "scores": [], "po": 0, "title": 0, "final": 0, "close_w": 0, "close_l": 0})
    weeks = defaultdict(list)
    for g in games:
        for me, mp, op in ((g[3], g[4], g[6]), (g[5], g[6], g[4])):
            k = (g[0], me)
            e = t[k]
            if not g[7]:
                e["w"] += mp > op
                e["l"] += mp < op
                e["pf"] += mp
                e["scores"].append(mp)
                weeks[(g[0], g[1])].append((me, mp))
                if abs(mp - op) < 5:
                    e["close_w"] += mp > op
                    e["close_l"] += mp < op
            elif g[8] in REAL:
                e["po"] = 1
                if g[8] == "Championship":
                    e["final"] = 1
                    e["title"] += mp > op
    return t, weeks


def build_awards(ctx, history, trades, drafts, waivers):
    games = history["games"]
    managers = history["managers"]
    current = set(history["current"])
    real = [h for h in managers if not managers[h].get("hidden")]
    t, weeks = _season_tables(games)

    career = defaultdict(lambda: {"seasons": set(), "w": 0, "l": 0, "pf": 0.0, "g": 0, "titles": 0,
                                  "finals": 0, "po": 0, "scores": [], "close_w": 0, "close_l": 0, "last": 0})
    for (season, h), e in t.items():
        c = career[h]
        c["seasons"].add(season)
        c["w"] += e["w"]; c["l"] += e["l"]; c["pf"] += e["pf"]; c["g"] += e["w"] + e["l"]
        c["titles"] += e["title"]; c["finals"] += e["final"]; c["po"] += e["po"]
        c["scores"] += e["scores"]; c["close_w"] += e["close_w"]; c["close_l"] += e["close_l"]
    # last place by regular-season record, finished seasons only
    for season in {s for s, _ in t}:
        if season == ctx["season"]:
            continue
        rows = [(h, e) for (s, h), e in t.items() if s == season and e["w"] + e["l"] >= 5]
        if rows:
            worst = sorted(rows, key=lambda r: (r[1]["w"], r[1]["pf"]))[0][0]
            career[worst]["last"] += 1
    # all-play luck
    luck = defaultdict(float)
    for (season, week), list_ in weeks.items():
        for h, p in list_:
            beat = sum(1 for o, q in list_ if o != h and q < p)
            of = len(list_) - 1
            luck[h] += (1 if p > max([q for o, q in list_ if o != h], default=-1) else 0) * 0  # placeholder
    exp = defaultdict(float)
    act = defaultdict(float)
    for (season, week), list_ in weeks.items():
        for h, p in list_:
            others = [q for o, q in list_ if o != h]
            if not others:
                continue
            exp[h] += sum(1 for q in others if q < p) / len(others)
    for h, c in career.items():
        act[h] = c["w"]
    # Week-to-week swing only compares fairly inside one scoring system, so the
    # consistency awards use the PPR era and say so.
    MODERN_FROM = 2014
    modern = defaultdict(list)
    for (season, h), e in t.items():
        if season >= MODERN_FROM:
            modern[h] += e["scores"]
    steady_seasons = sorted({s for s, _ in t if s >= MODERN_FROM})
    steady_from = steady_seasons[0] if steady_seasons else MODERN_FROM
    stdev = {}
    for h, xs in modern.items():
        if len(xs) >= 20:
            m = sum(xs) / len(xs)
            sd = (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5
            stdev[h] = round(100 * sd / m, 1) if m else None    # percent of their own average

    tm = trades["managers"]
    wm = waivers["managers"]
    dm = drafts["managers"]
    txn_per_season = {h: round((wm.get(h, {}).get("adds", 0) + tm.get(h, {}).get("n", 0)) / max(1, len(career[h]["seasons"])), 1)
                      for h in career}
    best_pick = {}
    for p in drafts["picks"]:
        if p[7]:
            continue
        if p[9] > best_pick.get(p[3], (None, -1e9))[1]:
            best_pick[p[3]] = ((f"{p[4]} ({p[0]} round {p[1]})"), p[9])
    big_weeks = Counter()
    top_week = {}
    for g in games:
        for me, mp in ((g[3], g[4]), (g[5], g[6])):
            if mp >= 150:
                big_weeks[me] += 1
            if mp > top_week.get(me, (0, None))[0]:
                top_week[me] = (mp, f"{g[0]} week {g[1]}")
    best_pickup = {}
    for p in waivers["pickups"]:
        if p["pts"] > best_pickup.get(p["h"], (None, -1))[1]:
            best_pickup[p["h"]] = (f"{p['n']} ({p['season']})", p["pts"])

    def rate_ok(h):
        return len(career[h]["seasons"]) >= MIN_SEASONS

    cards = [
        dict(key="titles", emoji="🏆", name="Most titles", note="Championships won",
             vals={h: c["titles"] for h, c in career.items()}, fmt="{v}", minv=1),
        dict(key="winpct", emoji="📈", name="Best win percentage", note="Regular season, 3+ seasons",
             vals={h: round(100 * c["w"] / max(1, c["g"]), 1) for h, c in career.items() if rate_ok(h) and c["g"] >= 26}, fmt="{v}%"),
        dict(key="points", emoji="💯", name="Most points all time", note="Regular season",
             vals={h: round(c["pf"]) for h, c in career.items()}, fmt="{v}"),
        dict(key="bigweek", emoji="🚀", name="Highest single week", note="Any game on record",
             vals={h: v[0] for h, v in top_week.items()}, extra={h: v[1] for h, v in top_week.items()}, fmt="{v}"),
        dict(key="big150", emoji="🎆", name="Most 150-point weeks", note="Games of 150 or more",
             vals=dict(big_weeks), fmt="{v}", minv=1),
        dict(key="trader", emoji="💱", name="Best trader", note="Points gained minus points given up",
             vals={h: round(m["in"] - m["out"], 1) for h, m in tm.items()}, fmt="{v}"),
        dict(key="dealmaker", emoji="🤝", name="Most trades", note="Trades completed",
             vals={h: m["n"] for h, m in tm.items()}, fmt="{v}", minv=1),
        dict(key="waiver", emoji="🧲", name="Best waiver claimer", note="Points from players picked up",
             vals={h: m["pts"] for h, m in wm.items()},
             extra={h: "%d claims" % m["adds"] for h, m in wm.items()}, fmt="{v}"),
        dict(key="pickup", emoji="🎣", name="Best single pickup", note="One waiver claim, points it scored",
             vals={h: round(v[1], 1) for h, v in best_pickup.items()},
             extra={h: v[0] for h, v in best_pickup.items()}, fmt="{v}"),
        dict(key="faab", emoji="💵", name="Best value per FAAB dollar", note="Points per dollar spent, $50 minimum",
             vals={h: m["per_dollar"] for h, m in wm.items() if m.get("per_dollar")}, fmt="{v}"),
        dict(key="active", emoji="⚡", name="Most active manager", note="Adds and trades per season",
             vals=txn_per_season, fmt="{v}"),
        dict(key="drafter", emoji="🎯", name="Best drafter", note="Average points a pick beat its round by",
             vals={h: m["avg"] for h, m in dm.items() if m["n"] >= 30}, fmt="{v}"),
        dict(key="steal", emoji="🕵️", name="Biggest draft steal", note="One pick, versus its round",
             vals={h: round(v[1], 1) for h, v in best_pick.items()}, extra={h: v[0] for h, v in best_pick.items()}, fmt="+{v}"),
        dict(key="playoffs", emoji="🎟️", name="Most playoff trips", note="Seasons reaching a real playoff round",
             vals={h: c["po"] for h, c in career.items()}, fmt="{v}", minv=1),
        dict(key="ironman", emoji="🧱", name="Longest tenure", note="Seasons played",
             vals={h: len(c["seasons"]) for h, c in career.items()}, fmt="{v}"),
        dict(key="lucky", emoji="🍀", name="Luckiest career", note="Wins above what the scores deserved",
             vals={h: round(act[h] - exp[h], 1) for h in career if rate_ok(h)}, fmt="+{v}"),
        dict(key="unlucky", emoji="🥀", name="Unluckiest career", note="Wins below what the scores deserved",
             vals={h: round(exp[h] - act[h], 1) for h in career if rate_ok(h)}, fmt="{v}"),
        dict(key="steady", emoji="🧘", name="Most consistent scorer",
             note="Smallest week-to-week swing against their own average, %d on" % steady_from,
             vals={h: -v for h, v in stdev.items() if v and rate_ok(h)},
             show={h: v for h, v in stdev.items() if v and rate_ok(h)}, fmt="{v}% swing"),
        dict(key="swings", emoji="🎢", name="Biggest boom or bust",
             note="Largest week-to-week swing against their own average, %d on" % steady_from,
             vals={h: v for h, v in stdev.items() if v and rate_ok(h)}, fmt="{v}% swing"),
        dict(key="heartbreak", emoji="💔", name="Most losses by under 5", note="Close losses",
             vals={h: c["close_l"] for h, c in career.items()}, fmt="{v}", minv=1),
        dict(key="escape", emoji="😅", name="Most wins by under 5", note="Close wins",
             vals={h: c["close_w"] for h, c in career.items()}, fmt="{v}", minv=1),
        dict(key="toilet", emoji="🚽", name="Most last-place finishes", note="Worst regular-season record",
             vals={h: c["last"] for h, c in career.items()}, fmt="{v}", minv=1),
    ]

    out, by_manager = [], defaultdict(list)
    for c in cards:
        vals = {h: v for h, v in c["vals"].items() if h in real and v is not None and v >= c.get("minv", -1e9)}
        if not vals:
            continue
        ranked = sorted(vals.items(), key=lambda kv: -kv[1])[:3]
        show = c.get("show", {})
        podium = [{"h": h, "v": show.get(h, v), "note": (c.get("extra") or {}).get(h)} for h, v in ranked]
        out.append({"key": c["key"], "emoji": c["emoji"], "name": c["name"], "note": c["note"],
                    "fmt": c["fmt"], "podium": podium, "current": ranked[0][0] in current})
        by_manager[ranked[0][0]].append({"key": c["key"], "emoji": c["emoji"], "name": c["name"],
                                         "v": show.get(ranked[0][0], ranked[0][1]), "fmt": c["fmt"]})
    data = {"generated": now(), "awards": out, "byManager": by_manager}
    ctx["write_json"](os.path.join(ctx["static"], "awards.json"), data, compact=True)
    return data
