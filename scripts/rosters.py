"""Current rosters: who is on them, how old they are, and how they got there.

Written by extras.build_all into static/data/rosters.json.

Ages come from the Sleeper player file the Season class already caches, computed
from birth_date so they stay right between refreshes. A player whose arrival
cannot be traced in the draft, trade or waiver records is marked "unknown"
rather than guessed at.
"""
import os
from collections import defaultdict
from datetime import date, datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


BUCKETS = [(0, 23, "23 and under"), (24, 26, "24 to 26"),
           (27, 29, "27 to 29"), (30, 99, "30 and over")]


def _age(p):
    """Age from birth_date when it is there, else whatever the file says."""
    bd = p.get("birth_date")
    if bd:
        try:
            y, m, d = (int(x) for x in bd.split("-")[:3])
            t = date.today()
            return t.year - y - ((t.month, t.day) < (m, d))
        except Exception:
            pass
    return p.get("age")


def _bucket(age):
    for lo, hi, label in BUCKETS:
        if lo <= age <= hi:
            return label
    return None


def _acquisition(h, key, season, drafts, trades, waivers, pkey):
    """The most recent way this manager got this player, or None.

    Later events win, so a player drafted in 2019 and re-acquired in a 2023
    trade reads as the trade.
    """
    best = None

    def offer(rank, s, w, kind, detail):
        nonlocal best
        cand = (s, w, rank)
        if best is None or cand > best[0]:
            best = (cand, {"kind": kind, "season": s, "detail": detail})

    for p in drafts.get("picks", ()):
        # season, round, pick, manager, player, pos, value, live, draft, over
        if p[3] == h and pkey(p[4]) == key and p[0] <= season:
            label = "round %s" % p[1]
            if p[8]:
                label += " %s" % p[8]
            offer(0, p[0], 0, "draft", label)

    for t in trades.get("trades", ()):
        side = (t.get("sides") or {}).get(h)
        if not side or t["season"] > season:
            continue
        # entries in "got" are {n, p, pts, st}, not bare names
        if any(pkey(g.get("n") if isinstance(g, dict) else g) == key
               for g in (side.get("got") or ())):
            others = [o for o in (t.get("sides") or {}) if o != h]
            offer(2, t["season"], t.get("week") or 0, "trade",
                  "from %s" % others[0] if others else "trade")

    for p in waivers.get("pickups", ()):
        if p["h"] == h and pkey(p["n"]) == key and p["season"] <= season:
            offer(1, p["season"], 0, "waiver",
                  ("$%s" % p["faab"]) if p.get("faab") else "free agent")

    return best[1] if best else None


GROUPS = ["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX", "BENCH"]
SKIP_SLOTS = {"K", "DEF", "DL", "LB", "DB", "IDP_FLEX"}


def _slot_map(league, roster):
    """player id -> the lineup slot he is filling.

    Sleeper's starters array lines up with the league's roster_positions once
    the bench entries are dropped, so the real slot is read off rather than
    guessed from the player's position. That matters in superflex, and in any
    league whose slot counts are not the usual ones.
    """
    slots = [s for s in (league.get("roster_positions") or []) if s not in ("BN", "IR", "TAXI")]
    out = {}
    for pid, slot in zip(roster.get("starters") or [], slots):
        if pid and pid != "0":
            out[pid] = slot
    return out


def _load_ecr(ctx):
    """FantasyPros expert consensus, positional rank, as a name -> rank map.

    Redraft leagues get rest-of-season, dynasty leagues get dynasty. The file
    is a dated snapshot pulled through the FantasyPros connector by hand, not
    a live feed, so everything built off it is labelled with that date.
    """
    from extras import pkey
    raw = ctx["read_json"](os.path.join(ctx["data"], "ecr.json"), {}) or {}
    kind = "DYNASTY" if ctx.get("dynasty") else "ROS"
    m, floor = {}, {}
    for pos, names in (raw.get(kind) or {}).items():
        for name, rank in names.items():
            m[(pos, pkey(name))] = rank
        # a player nobody ranked is not "unrated", he is worse than everyone on
        # the list. Counting him one past the end keeps a thin bench from
        # outscoring a deep one just by having fewer rankable players on it.
        floor[pos] = len(names) + 1
    return {"map": m, "floor": floor, "kind": kind, "asof": raw.get("generated"),
            "scoring": raw.get("scoring"), "source": raw.get("source")}


def build_rosters(ctx, rows, drafts, trades, waivers):
    from extras import pkey

    ecr = _load_ecr(ctx)
    ecr_map, ecr_floor = ecr["map"], ecr["floor"]

    cur = ctx["cur"]
    season = ctx["season"]
    blob = cur.players or {}
    dynasty = bool(ctx.get("dynasty"))

    # points this player has scored while started, for this manager, and how
    # many starts that took, so a per-start rate can be compared fairly
    career, this_season = defaultdict(float), defaultdict(float)
    career_n, season_n = defaultdict(int), defaultdict(int)
    for s, w, h, k, name, pos, started, pts in rows:
        if not started:
            continue
        career[(h, k)] += pts
        career_n[(h, k)] += 1
        if s == season:
            this_season[(h, k)] += pts
            season_n[(h, k)] += 1

    # a player's record anywhere in this league, not just with this manager,
    # so a newly acquired player still carries his history
    league_pts, league_n = defaultdict(float), defaultdict(int)
    for s, w, h, k, name, pos, started, pts in rows:
        if started:
            league_pts[k] += pts
            league_n[k] += 1

    # the earliest draft on record, for "still here from the startup"
    first_draft = min((p[0] for p in drafts.get("picks", ())), default=None)
    startup_picks = {(p[3], pkey(p[4])) for p in drafts.get("picks", ())
                     if first_draft and p[0] == first_draft}

    out, ages_all = {}, []
    for r in cur.rosters:
        h = cur.handle.get(r.get("roster_id"))
        if not h:
            continue
        starters = set(r.get("starters") or [])
        smap = _slot_map(cur.league, r)
        players = []
        for pid in (r.get("players") or []):
            info = cur.pinfo(pid)
            meta = blob.get(pid) or {}
            key = pkey(info["name"])
            age = _age(meta)
            players.append({
                "id": pid, "n": info["name"], "p": info["pos"], "t": info["team"],
                "age": age, "exp": meta.get("years_exp"),
                "inj": meta.get("injury_status") or None,
                "st": pid in starters,
                "slot": smap.get(pid),
                "pts": round(career.get((h, key), 0.0), 1),
                "now": round(this_season.get((h, key), 0.0), 1),
                "src": _acquisition(h, key, season, drafts, trades, waivers, pkey),
                "startup": bool(first_draft and (h, key) in startup_picks),
                "rate": (round(league_pts[key] / league_n[key], 1)
                         if league_n[key] >= 3 else None),
                "ecr": ecr_map.get((info["pos"], key)),
            })
        players.sort(key=lambda x: (not x["st"], x["p"] or "", -(x["pts"] or 0)))

        # position groups: what each is producing now, and what it has produced
        # per start across this league's whole history
        groups = defaultdict(lambda: {"now": 0.0, "rate": 0.0, "n": 0, "rated": 0,
                                      "ecr": 0.0, "ecrn": 0, "ecrtot": 0})
        for p in players:
            if p["st"]:
                g = p["slot"]
                if g in SKIP_SLOTS or g not in GROUPS:
                    continue
            else:
                g = "BENCH"
                if p["p"] in SKIP_SLOTS:
                    continue
            e = groups[g]
            e["n"] += 1
            e["now"] += p["now"]
            if p["rate"] is not None:
                e["rate"] += p["rate"]
                e["rated"] += 1
            fl = ecr_floor.get(p["p"])
            if p["ecr"] is not None:
                e["ecr"] += p["ecr"]
                e["ecrn"] += 1
                e["ecrtot"] += 1
            elif fl:
                # ranked at a position FantasyPros covers, but off the list
                e["ecr"] += fl
                e["ecrtot"] += 1
        group_out = {}
        for g in GROUPS:
            e = groups.get(g)
            if not e or not e["n"]:
                continue
            group_out[g] = {"n": e["n"], "now": round(e["now"], 1),
                            "rate": round(e["rate"] / e["rated"], 1) if e["rated"] else None,
                            "rated": e["rated"],
                            # averaged over everyone at a covered position, with
                            # the unranked counted at the floor; ecrn/ecrtot says
                            # how many of them the experts actually ranked
                            "ecr": round(e["ecr"] / e["ecrtot"], 1) if e["ecrtot"] else None,
                            "ecrn": e["ecrn"], "ecrtot": e["ecrtot"]}

        real = [p for p in players if p["age"]]
        st_real = [p for p in real if p["st"]]
        by_pos = defaultdict(list)
        for p in real:
            by_pos[p["p"]].append(p["age"])
        buckets = defaultdict(int)
        for p in real:
            b = _bucket(p["age"])
            if b:
                buckets[b] += 1

        avg_all = round(sum(p["age"] for p in real) / len(real), 1) if real else None
        avg_st = round(sum(p["age"] for p in st_real) / len(st_real), 1) if st_real else None
        if avg_all:
            ages_all.append((h, avg_all))

        by_src = defaultdict(lambda: {"n": 0, "pts": 0.0})
        for p in players:
            kind = (p["src"] or {}).get("kind") or "unknown"
            by_src[kind]["n"] += 1
            by_src[kind]["pts"] += p["pts"]

        out[h] = {
            "players": players,
            "age": {"all": avg_all, "starters": avg_st,
                    "byPos": {k: round(sum(v) / len(v), 1) for k, v in sorted(by_pos.items())},
                    "buckets": {lab: buckets.get(lab, 0) for _lo, _hi, lab in BUCKETS},
                    "oldest": max(real, key=lambda p: p["age"], default=None),
                    "youngest": min(real, key=lambda p: p["age"], default=None)},
            "groups": group_out,
            "sources": {k: {"n": v["n"], "pts": round(v["pts"], 1)} for k, v in by_src.items()},
            "startup_held": sum(1 for p in players if p["startup"]),
            "injured": [p for p in players if p["inj"]],
        }

    # youngest roster to oldest, so a manager page can say where it sits
    ages_all.sort(key=lambda x: x[1])
    for i, (h, _a) in enumerate(ages_all):
        out[h]["rank_young"] = i + 1
    for h in out:
        out[h]["of"] = len(ages_all)

    # rank every manager inside each position group, on both measures
    board = {}
    for g in GROUPS:
        board[g] = {}
        for field in ("now", "rate", "ecr"):
            have = [(h, m["groups"][g][field]) for h, m in out.items()
                    if m["groups"].get(g) and m["groups"][g].get(field) is not None]
            # points: more is better. ECR: it is a rank, so less is better.
            have.sort(key=lambda x: x[1] if field == "ecr" else -x[1])
            board[g][field] = [{"h": h, "v": v} for h, v in have]
            for i, (h, _v) in enumerate(have):
                out[h]["groups"][g].setdefault("rank", {})[field] = i + 1
        for h, m in out.items():
            if m["groups"].get(g):
                m["groups"][g]["of"] = len(board[g]["rate"]) or len(board[g]["now"])

    data = {"generated": now(), "season": season, "dynasty": dynasty,
            "ecr": {k: ecr[k] for k in ("kind", "asof", "scoring", "source")},
            "first_draft": first_draft,
            "league_age": (round(sum(a for _h, a in ages_all) / len(ages_all), 1)
                           if ages_all else None),
            "board": board, "managers": out}
    ctx["write_json"](os.path.join(ctx["static"], "rosters.json"), data, compact=True)
    return data
