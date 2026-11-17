"""extras.py - the data behind Playoff Odds, Week Preview, Trades, Draft Grades and Players.

Called from update_site.py after history.json is built. Everything here is
recomputed from scratch each run.

Definitions (repeated on the pages that show them):
  Trade value  Points a player scored WHILE STARTED for the manager who got him,
               from the trade week on. Redraft: that season only. Dynasty: every
               later season he stayed with that manager.
  Pick value   Points the player scored WHILE STARTED for the manager who drafted
               him (redraft: that season; dynasty: every season he stayed).
               A pick is graded against the average pick in the same round.
  Odds         10,000 simulated finishes. Each team scores from a normal curve
               centred on its scoring this season, pulled toward last season and
               the league average while the sample is small. Each simulation also
               redraws how good every team really is, so early-season odds stay modest.
"""
import json
import math
import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

SIMS = 10000
SHRINK_GAMES = 4          # prior weight, in games
REAL = {"Quarterfinal", "Semifinal", "Championship"}

SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?", re.I)


def pkey(name):
    s = re.sub(r"\s*-\s*DEF$", "", (name or "").strip(), flags=re.I).lower().replace("&#39;", "'")
    s = SUFFIX.sub("", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- yahoo era
def yahoo_era(ctx):
    """Pre-2014 rosters and drafts, or None when this league has no Yahoo era.

    Returns (lineup_rows, drafts, coverage, top_games). A season whose coverage
    is not complete has totals for the scraped weeks only, not the full season.
    """
    if ctx["mode"] != "vault":
        return None
    try:
        import yahoo_lineups_api as YL
        return YL.lineups(), YL.drafts(), YL.coverage(), YL.top_games()
    except Exception:
        return None


def yahoo_label(cov, season):
    """'' for a full season, else 'weeks 1-5, 11-16'."""
    c = cov.get(season)
    if not c or c.get("complete"):
        return ""
    w = c["weeks"]
    runs, start = [], w[0]
    for a, b in zip(w, w[1:] + [None]):
        if b != (a + 1):
            runs.append(str(start) if start == a else "%d-%d" % (start, a))
            start = b
    return "weeks " + ", ".join(runs)


# ---------------------------------------------------------------- lineups
def collect_slots(ctx):
    """(season, week, handle, key, name, pos, started, points) for every rostered player-week."""
    rows = []
    if ctx["mode"] == "vault":
        import flp
        for s in ctx["flp_slots"]:
            if s.season >= ctx["season"]:
                continue
            nm = flp.norm_player(s.player)
            rows.append((s.season, s.week, s.manager, pkey(nm), nm, s.pos or "", bool(s.started), round(s.points or 0, 2)))
    for S in ctx["live_seasons"]:
        for w in S.completed_weeks(ctx["state"]):
            for m in S.matchups(w):
                rid = m.get("roster_id")
                h = S.handle.get(rid)
                if not h:
                    continue
                starters = set(m.get("starters") or [])
                pp = m.get("players_points") or {}
                for pid in m.get("players") or []:
                    info = S.pinfo(pid)
                    ctx.setdefault("pid_of", {})[pkey(info["name"])] = pid
                    rows.append((S.season, w, h, pkey(info["name"]), info["name"], info["pos"],
                                 pid in starters, round(pp.get(pid, 0) or 0, 2)))
    return rows


def started_index(rows):
    """(handle, key) -> [(season, week, points)] for started weeks only."""
    idx = defaultdict(list)
    for season, week, h, k, _n, _p, st, pts in rows:
        if st:
            idx[(h, k)].append((season, week, pts))
    return idx


def value_after(idx, h, k, season, week, dynasty, until=None):
    tot, starts = 0.0, 0
    for s, w, pts in idx.get((h, k), ()):
        if (s, w) < (season, week or 0):
            continue
        if not dynasty and s != season:
            continue
        tot += pts
        starts += 1
    return round(tot, 2), starts


# ---------------------------------------------------------------- players
def _unit_name(name, pos):
    """One name per defence: 'Pittsburgh Steelers' and 'Steelers' are the same unit."""
    if pos == "DEF":
        parts = re.sub(r"\s*-?\s*DEF$", "", (name or "").strip(), flags=re.I).split()
        if len(parts) > 1:
            return parts[-1]
    return name


def _sleeper_ids(ctx, per):
    """key -> Sleeper id (a team code for a defence), for headshots and logos."""
    ids = dict(ctx.get("pid_of") or {})
    try:
        allp = ctx["cur"].players
    except Exception:
        allp = {}
    by_name, by_def = defaultdict(list), {}
    for pid, p in allp.items():
        if (p.get("position") == "DEF") or not str(pid).isdigit():
            if p.get("last_name"):
                by_def[pkey(p["last_name"])] = pid
            continue
        nm = p.get("full_name") or ("%s %s" % (p.get("first_name", ""), p.get("last_name", ""))).strip()
        if nm:
            by_name[pkey(nm)].append((pid, p.get("position") or "", p.get("years_exp") or 0))
    out = {}
    for k, p in per.items():
        if p["p"] == "DEF":
            if k in by_def:
                out[k] = by_def[k]
            continue
        if k in ids and str(ids[k]).isdigit():
            out[k] = ids[k]
            continue
        cands = [c for c in by_name.get(k, ()) if c[1] == p["p"]]
        if len(cands) == 1:
            out[k] = cands[0][0]
        elif len(cands) > 1:      # two players, one name: the longer career is the one with history here
            out[k] = max(cands, key=lambda c: c[2])[0]
    return out


def build_players(ctx, rows):
    per = {}
    tops = []
    for season, week, h, k, name, pos, st, pts in rows:
        if pos == "DEF":
            name = _unit_name(name, pos)
            k = pkey(name)
        p = per.setdefault(k, {"n": name, "p": pos, "pts": 0.0, "st": 0, "wk": 0, "b": 0.0, "s": {}})
        if pos and not p["p"]:
            p["p"] = pos
        if season >= p.get("last", 0):
            p["n"], p["last"] = name, season
        e = p["s"].setdefault((season, h), [0.0, 0, 0, 0.0])
        e[2] += 1
        p["wk"] += 1
        if st:
            e[0] += pts
            e[1] += 1
            p["pts"] += pts
            p["st"] += 1
            tops.append((pts, season, week, h, name, pos))
        else:
            e[3] += pts
            p["b"] += pts
    ye = yahoo_era(ctx)
    if ye:
        ylines, _ydrafts, _ycov, ytops = ye
        # yahoo_era serves season TOTALS from yahoo_lineups_api, which covers
        # 2008-2013. Since 2026-11-16 flp.slots() covers those same four seasons
        # week by week, so `rows` already holds them and merging both counted
        # every pre-2014 player-season twice: doubled career points, a duplicate
        # season row per player, and each pre-2014 top game listed twice. The
        # totals source now contributes only what the week-level data lacks,
        # which keeps it working for any season that is ever scraped at season
        # level only.
        covered = {season for season, *_ in rows}
        if covered:
            ylines = [r for r in ylines if r[0] not in covered]
            ytops = [t for t in ytops if t[0] not in covered]
        ypos = {}
        for season, h, name, pos, pts, starts, weeks in ylines:
            if pos == "DEF":
                name = _unit_name(name, pos)
            k = pkey(name)
            if pos:
                ypos.setdefault(k, pos)
            p = per.setdefault(k, {"n": name, "p": pos, "pts": 0.0, "st": 0, "wk": 0, "b": 0.0, "s": {}})
            if pos and not p["p"]:
                p["p"] = pos
            e = p["s"].setdefault((season, h), [0.0, 0, 0, 0.0])
            e[0] += pts
            e[1] += starts
            e[2] += weeks
            p["pts"] += pts
            p["st"] += starts
            p["wk"] += weeks
        for season, week, h, name, pts in ytops:
            tops.append((pts, season, week, h, name, ypos.get(pkey(name), "")))
    ids = _sleeper_ids(ctx, per)
    out = []
    for k, p in per.items():
        if p["pts"] < 25 and p["st"] < 3:
            continue
        # season rows: [season, manager, points started, starts, weeks rostered, points on the bench]
        seasons = sorted(([s, h, round(v[0], 2), v[1], v[2], round(v[3], 2)] for (s, h), v in p["s"].items()),
                         key=lambda x: (x[0], -x[2]))
        row = {"k": k, "n": p["n"], "p": p["p"], "pts": round(p["pts"], 2), "st": p["st"],
               "wk": p["wk"], "b": round(p["b"], 2), "s": seasons}
        if k in ids:
            row["id"] = ids[k]
        out.append(row)
    out.sort(key=lambda x: -x["pts"])
    tops.sort(key=lambda x: -x[0])
    first = min((r[0] for r in rows), default=ctx["season"])
    if ye:
        first = min([first] + [s for s, *_ in ye[0]])
    data = {
        "generated": now(),
        "first_season": first,
        "pre2014_standard_scoring": bool(ye),
        # bench points exist from the first season with week-by-week lineups
        "bench_from": min((r[0] for r in rows), default=ctx["season"]),
        "players": out,
        "top_games": [{"pts": t[0], "season": t[1], "week": t[2], "h": t[3], "n": t[4], "p": t[5]} for t in tops[:40]],
    }
    ctx["write_json"](os.path.join(ctx["static"], "players.json"), data, compact=True)
    return data


# ---------------------------------------------------------------- trades
def _grade_trade(sides):
    ranked = sorted(sides.items(), key=lambda kv: -kv[1]["value"])
    winner = ranked[0][0] if len(ranked) > 1 and ranked[0][1]["value"] > ranked[1][1]["value"] else None
    margin = round(ranked[0][1]["value"] - ranked[1][1]["value"], 2) if len(ranked) > 1 else 0
    return winner, margin


def _pick_results(ctx):
    """(season, round, original roster_id) -> the player a traded pick became
    (T.J., 2026-11-11). Sleeper only. The original owner of each selection comes
    from the draft's slot_to_roster_id, which only the single-draft endpoint
    carries. A draft that has not happened yet has no entry, so its picks keep
    their plain "2027 round 2" label."""
    out = {}
    for S in ctx["live_seasons"]:
        try:
            drafts = ctx["sleeper"](f"/league/{S.league_id}/drafts") or []
        except Exception:
            continue
        for d in drafts:
            if d.get("status") != "complete":
                continue
            try:
                full = ctx["sleeper"](f"/draft/{d['draft_id']}") or {}
                dp = ctx["sleeper"](f"/draft/{d['draft_id']}/picks") or []
            except Exception:
                continue
            s2r = full.get("slot_to_roster_id") or {}
            teams = (full.get("settings") or {}).get("teams") or len(s2r) or 12
            # same test build_drafts uses to tell a rookie draft from a startup draft
            rookie = ((full.get("settings") or d.get("settings") or {}).get("rounds") or 99) <= 6
            user_h = {S.owner[r]: h for r, h in S.handle.items() if r in S.owner}
            for pk in dp:
                orig = s2r.get(str(pk.get("draft_slot")))
                if orig is None or not pk.get("player_id"):
                    continue
                info = S.pinfo(pk.get("player_id"))
                no = pk.get("pick_no") or 0
                out[(int(S.season), pk.get("round"), int(orig))] = {
                    "n": info["name"], "p": info["pos"], "rookie": rookie,
                    "slot": f"{pk.get('round')}.{((no - 1) % teams) + 1:02d}" if no else "",
                    "by": S.handle.get(pk.get("roster_id")) or user_h.get(pk.get("picked_by"))}
    return out


def build_trades(ctx, rows):
    idx = started_index(rows)
    dyn = ctx["dynasty"]
    trades = []
    try:
        pick_results = _pick_results(ctx)
    except Exception:
        pick_results = {}
    if ctx["mode"] == "vault":
        import flp_trade_value as TV
        for t in TV.trades():
            if t["season"] >= ctx["season"]:
                continue
            sides = {}
            for h, side in t["sides"].items():
                sides[h] = {"got": [{"n": r["player"], "p": r["pos"], "pts": r["points"], "st": r["starts"]}
                                    for r in side["acquired"]], "picks": [], "value": side["value"]}
            weeks = [r["from_week"] for s in t["sides"].values() for r in s["acquired"] if r["from_week"]]
            trades.append({"season": t["season"], "week": min(weeks) if weeks else None, "era": t["era"],
                           "sides": sides, "winner": t["winner"], "margin": t["margin"], "live": False})
    for S in ctx["live_seasons"]:
        live = S.season == ctx["season"]
        for leg in range(0, 19):
            try:
                txs = ctx["sleeper"](f"/league/{S.league_id}/transactions/{leg}") or []
            except Exception:
                continue
            for tx in txs:
                if tx.get("type") != "trade" or tx.get("status") != "complete":
                    continue
                week = tx.get("leg") or leg or 1
                adds = tx.get("adds") or {}
                sides = {}
                for rid in tx.get("roster_ids") or []:
                    h = S.handle.get(rid)
                    if not h:
                        continue
                    got = []
                    for pid, to in adds.items():
                        if to != rid:
                            continue
                        info = S.pinfo(pid)
                        pts, st = value_after(idx, h, pkey(info["name"]), S.season, week, dyn)
                        got.append({"n": info["name"], "p": info["pos"], "pts": pts, "st": st})
                    picks = []
                    pick_pts = 0.0
                    for p in (tx.get("draft_picks") or []):
                        if p.get("owner_id") != rid:
                            continue
                        label = f"{p.get('season')} round {p.get('round')}"
                        try:
                            res = pick_results.get((int(p.get("season")), p.get("round"), int(p.get("roster_id"))))
                        except (TypeError, ValueError):
                            res = None
                        if res:
                            label += f": {res['n']}{(' ' + res['p']) if res['p'] else ''}"
                            if res["slot"]:
                                label += f" ({res['slot']})"
                            if res["by"] and res["by"] != h:
                                label += ", used by %s" % ctx.get("shown", str)(res["by"])
                            elif res["by"] == h and res["rookie"]:
                                # He made the pick himself, so it counts like an acquired
                                # player: what the drafted player scored in his lineup from
                                # the draft season on. A pick he traded on scores nothing
                                # here; what he got for it is graded in that later trade.
                                # Rookie drafts only (T.J., 2026-11-11): startup draft pick
                                # swaps are shown but not scored, or they swamp the page.
                                ppts, _pst = value_after(idx, h, pkey(res["n"]), int(p.get("season")), 0, dyn)
                                pick_pts += ppts
                                label += f", {round(ppts, 1)} pts"
                        picks.append(label)
                    faab = sum((w.get("amount") or 0) for w in (tx.get("waiver_budget") or []) if w.get("receiver") == rid)
                    if faab:
                        picks.append(f"${faab} FAAB")
                    sides[h] = {"got": got, "picks": picks, "value": round(sum(g["pts"] for g in got) + pick_pts, 2)}
                if len(sides) < 2:
                    continue
                winner, margin = _grade_trade(sides)
                trades.append({"season": S.season, "week": week, "era": "sleeper", "sides": sides,
                               "winner": winner, "margin": margin, "live": live,
                               "ts": tx.get("status_updated") or tx.get("created")})
    trades.sort(key=lambda t: (t["season"], t["week"] or 0, t.get("ts") or 0))
    per = defaultdict(lambda: {"n": 0, "w": 0, "l": 0, "t": 0, "in": 0.0, "out": 0.0, "partners": Counter()})
    for t in trades:
        hs = list(t["sides"])
        for h in hs:
            e = per[h]
            e["n"] += 1
            e["in"] += t["sides"][h]["value"]
            for o in hs:
                if o != h:
                    e["out"] += t["sides"][o]["value"]
                    e["partners"][o] += 1
            if t["live"]:
                continue
            if t["winner"] == h:
                e["w"] += 1
            elif t["winner"] is None:
                e["t"] += 1
            else:
                e["l"] += 1
    managers = {h: {"n": e["n"], "w": e["w"], "l": e["l"], "t": e["t"], "in": round(e["in"], 1),
                    "out": round(e["out"], 1), "partner": (e["partners"].most_common(1) or [[None, 0]])[0]}
                for h, e in per.items()}
    data = {"generated": now(), "dynasty": dyn, "trades": trades, "managers": managers,
            "first_season": min((t["season"] for t in trades), default=None)}
    ctx["write_json"](os.path.join(ctx["static"], "trades.json"), data, compact=True)
    return data


def _draft_shrink(picks, managers):
    """How far to pull a short draft record toward the league average.

    A single pick is wildly noisy, so a manager with one season can top the
    all-time list on luck alone: before this, Brandon led it at +21.6 on 14
    picks, ahead of managers with 239. Rather than hide short records behind a
    cutoff, each manager's average is pulled toward the league mean by how
    little evidence stands behind it:

        shown = grand + (avg - grand) * n / (n + k)

    k is the number of picks at which a record is worth as much as the prior,
    and it is measured from the picks themselves, not chosen: k = W / B, where
    W is the variance of a single pick around its own manager's average and B
    is the real spread between managers. B uses the DerSimonian-Laird
    estimator, because the naive "spread of the averages minus the average
    noise" is dominated by the fourteen-pick teams and collapses to zero.

    On 2,808 finished picks this gives W about 4,170 (a pick swings some 65
    points) against B about 51 (real skill spans about 7 a pick), so k lands
    near 82 picks, five and a half seasons. Q was 54.9 on 23 degrees of
    freedom, so the spread between managers is real and not all noise.
    Returns None if there are too few picks to measure.
    """
    vals = defaultdict(list)
    for p in picks:
        if not p[7] and p[9] is not None:
            vals[p[3]].append(float(p[9]))
    rows = [(h, len(v), sum(v) / len(v), v) for h, v in vals.items() if len(v) > 1]
    if len(rows) < 3:
        return None
    N = sum(r[1] for r in rows)
    W = sum(sum((x - m) ** 2 for x in v) for _h, _n, m, v in rows) / N
    if W <= 0:
        return None
    wt = {h: n / W for h, n, _m, _v in rows}
    sw = sum(wt.values())
    grand = sum(wt[h] * m for h, _n, m, _v in rows) / sw
    Q = sum(wt[h] * (m - grand) ** 2 for h, _n, m, _v in rows)
    c = sw - sum(x * x for x in wt.values()) / sw
    B = max((Q - (len(rows) - 1)) / c, 0.0) if c > 0 else 0.0
    if B <= 0:                      # no measurable skill: show everyone at the mean
        k = None
    else:
        k = W / B
    for h, n, m, _v in rows:
        if h not in managers:
            continue
        adj = grand if k is None else grand + (m - grand) * n / (n + k)
        managers[h]["adj"] = round(adj, 1)
        managers[h]["wt"] = round(n / (n + k), 2) if k else 0.0
    return {"k": round(k) if k else None, "grand": round(grand, 2),
            "within": round(W), "between": round(B, 1), "q": round(Q, 1),
            "df": len(rows) - 1}


# ---------------------------------------------------------------- drafts
def build_drafts(ctx, rows):
    idx = started_index(rows)
    dyn = ctx["dynasty"]
    picks = []       # season, rnd, pick_no, h, name, pos, value, live, draft label
    if ctx["mode"] == "vault":
        import flp_draft as FD
        got, _problems = FD.all_picks(ctx["flp_slots"])
        for p in got:
            if p.season >= ctx["season"]:
                continue
            picks.append([p.season, p.rnd, p.pick_no, p.manager, p.player, p.pos or "", round(p.value, 2), False, ""])
        # some seasons in the vault notes carry every pick as round 1, with the pick number restarting each round.
        # Rebuild the round from how many times that pick number has already come up (T.J. spotted this 2026-11-13).
        _by = defaultdict(list)
        for _p in picks:
            _by[_p[0]].append(_p)
        for _season, _rows in _by.items():
            if sum(1 for _p in _rows if _p[1] == 1) > 2 * (len({_p[3] for _p in _rows}) or 1):
                _seen = defaultdict(int)
                for _p in _rows:
                    _seen[_p[2]] += 1
                    _p[1] = _seen[_p[2]]
    for S in ctx["live_seasons"]:
        try:
            drafts = ctx["sleeper"](f"/league/{S.league_id}/drafts") or []
        except Exception:
            drafts = []
        user_h = {S.owner[r]: h for r, h in S.handle.items() if r in S.owner}
        for d in drafts:
            if d.get("status") != "complete":
                continue
            try:
                dp = ctx["sleeper"](f"/draft/{d['draft_id']}/picks") or []
            except Exception:
                continue
            label = "Rookie draft" if dyn and (d.get("settings") or {}).get("rounds", 99) <= 6 else ("Startup draft" if dyn else "")
            for pk in dp:
                h = S.handle.get(pk.get("roster_id")) or user_h.get(pk.get("picked_by"))
                if not h:
                    continue
                info = S.pinfo(pk.get("player_id") or "")
                val, _ = value_after(idx, h, pkey(info["name"]), S.season, 0, dyn)
                picks.append([S.season, pk.get("round"), pk.get("pick_no"), h, info["name"], info["pos"], val,
                              S.season == ctx["season"], label])
    ye = yahoo_era(ctx)
    if ye:
        ylines, ydrafts, ycov, _ytops = ye
        yval, ypos = {}, {}
        for season, h, name, pos, pts, starts, _w in ylines:
            yval[(season, h, pkey(name))] = round(pts, 2)
            if pos:
                ypos.setdefault(pkey(name), pos)
        for season, got in sorted(ydrafts.items()):
            lab = yahoo_label(ycov, season)
            # some Yahoo seasons arrive with every pick marked round 1 and the pick number restarting each
            # round; rebuild the round from how many times that pick number has already come up (2026-11-13)
            _mgrs = len({pk["handle"] for pk in got}) or 1
            if sum(1 for pk in got if pk["round"] == 1) > 2 * _mgrs:
                _seen = defaultdict(int)
                for pk in got:
                    _seen[pk["pick"]] += 1
                    pk["round"] = _seen[pk["pick"]]
            for pk in got:
                k = pkey(pk["player"])
                picks.append([season, pk["round"], pk["pick"], pk["handle"], pk["player"],
                              ypos.get(k, ""), yval.get((season, pk["handle"], k), 0.0), False, lab])
    base = defaultdict(list)
    for p in picks:
        base[(p[0], p[8], p[1])].append(p[6])
    base = {k: sum(v) / len(v) for k, v in base.items() if v}
    for p in picks:
        p.append(round(p[6] - base.get((p[0], p[8], p[1]), 0), 2))      # index 9: over round average
    # index 10: starts in the drafting manager's lineup behind that value; index 11: seasons it covers
    ystarts = {(season, h, pkey(name)): starts for season, h, name, _pos, _pts, starts, _w in ye[0]} if ye else {}
    for p in picks:
        k = pkey(p[4])
        st = ystarts.get((p[0], p[3], k))
        if st is None:
            st = value_after(idx, p[3], k, p[0], 0, dyn)[1]
        p.append(st)
        p.append(max(1, ctx["season"] - p[0] + 1) if dyn else 1)
    # grade each manager's draft within its season
    grades = defaultdict(dict)
    by = defaultdict(lambda: defaultdict(float))
    for p in picks:
        by[(p[0], p[8])][p[3]] += p[9]
    letters = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "D-", "F"]
    for (season, label), totals in by.items():
        order = sorted(totals.items(), key=lambda kv: -kv[1])
        n = len(order)
        for i, (h, tot) in enumerate(order):
            letter = letters[min(len(letters) - 1, int(i * len(letters) / max(1, n)))]
            grades[f"{season}{(' ' + label) if label else ''}"][h] = {"grade": letter, "over": round(tot, 1), "rank": i + 1}
    per = defaultdict(lambda: {"n": 0, "hits": 0, "over": 0.0})
    for p in picks:
        if p[7]:
            continue
        e = per[p[3]]
        e["n"] += 1
        e["over"] += p[9]
        e["hits"] += p[9] > 0
    managers = {h: {"n": e["n"], "hit": round(100 * e["hits"] / max(1, e["n"])), "avg": round(e["over"] / max(1, e["n"]), 1)}
                for h, e in per.items()}
    shrink = _draft_shrink(picks, managers)
    data = {"generated": now(), "dynasty": dyn, "shrink": shrink,
            "fields": ["season", "round", "pick", "manager", "player", "pos", "value", "live", "draft", "over", "starts", "seasons"],
            "picks": picks, "grades": grades, "managers": managers}
    ctx["write_json"](os.path.join(ctx["static"], "drafts.json"), data, compact=True)
    return data


# ---------------------------------------------------------------- costly games
def build_costly(ctx, rows):
    """Losses where one starter's shortfall was bigger than the margin.

    A player's normal is his average in that manager's starting lineup that
    season, excluding the week in question, and he needs three other starts
    before there is anything to compare against. Nothing here is an injury
    claim: it only says a starter came in under his own normal by more than the
    game was lost by.
    """
    # started points per (season, handle, player) and per (season, week, handle)
    by_player = defaultdict(dict)
    for season, week, h, k, name, pos, st, pts in rows:
        if st:
            by_player[(season, h, k)][week] = (pts, name, pos)

    lineup = defaultdict(list)
    for season, week, h, k, name, pos, st, pts in rows:
        if st:
            lineup[(season, week, h)].append(k)

    out = []
    for g in ctx["history"]["games"]:
        season, week, _era, a, pa, b, pb, playoff, label = g
        if pa == pb:
            continue
        loser, lp, wp = (b, pb, pa) if pa > pb else (a, pa, pb)
        margin = round(wp - lp, 2)
        winner = a if pa > pb else b
        for k in lineup.get((season, week, loser), ()):
            weeks = by_player.get((season, loser, k), {})
            other = [v[0] for w, v in weeks.items() if w != week]
            if len(other) < 3:
                continue
            got, name, pos = weeks[week]
            avg = sum(other) / len(other)
            short = round(avg - got, 2)
            if short < margin:
                continue
            out.append({"season": season, "week": week, "h": loser, "vs": winner,
                        "margin": margin, "lost": round(lp, 2), "won": round(wp, 2),
                        "n": name, "p": pos, "pts": round(got, 2), "avg": round(avg, 2),
                        "short": short, "playoff": bool(playoff), "label": label})
    # worst first, and only the biggest one per game
    out.sort(key=lambda x: -x["short"])
    seen, best = set(), []
    for c in out:
        key = (c["season"], c["week"], c["h"])
        if key in seen:
            continue
        seen.add(key)
        best.append(c)

    per = defaultdict(list)
    for c in best:
        if len(per[c["h"]]) < 8:
            per[c["h"]].append(c)
    data = {"generated": now(), "worst": best[:40], "byManager": per,
            "count": len(best)}
    ctx["write_json"](os.path.join(ctx["static"], "costly.json"), data, compact=True)
    return data


# ---------------------------------------------------------------- odds + previews
def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def team_models(ctx):
    """Expected weekly score per team.

    Redraft (FL Players): this season only. Rosters are redrawn every August, so
    last season's scoring says nothing about this team, and a team with few games
    is simply pulled toward the league average.
    Dynasty (FL Evolution): last season counts, because the roster carried over.
    """
    season = ctx["season"]
    games = ctx["history"]["games"]
    use_last = ctx["dynasty"] if ctx.get("odds_prior") is None else ctx["odds_prior"] == "last_season"
    cur = defaultdict(list)
    prev = defaultdict(list)
    for s, w, _e, a, pa, b, pb, playoff, _l in games:
        if playoff:
            continue
        if s == season:
            cur[a].append(pa); cur[b].append(pb)
        elif s == season - 1 and use_last:
            prev[a].append(pa); prev[b].append(pb)
    teams = sorted(set(ctx["cur"].handle.values()))
    allcur = [x for v in cur.values() for x in v]
    allprev = [x for v in prev.values() for x in v]
    lg_prev = statistics.mean(allprev) if allprev else None
    lg_cur = statistics.mean(allcur) if allcur else lg_prev or 100.0
    pool = allcur if (len(allcur) >= 24 or not use_last) else allcur + allprev
    sd = max(15.0, statistics.pstdev(pool)) if len(pool) >= 12 else 25.0
    models = {}
    for h in teams:
        xs = cur.get(h, [])
        if prev.get(h) and lg_prev:
            prior = lg_cur * (0.5 + 0.5 * statistics.mean(prev[h]) / lg_prev)
        else:
            prior = lg_cur
        n = len(xs)
        mu = (sum(xs) + SHRINK_GAMES * prior) / (n + SHRINK_GAMES)
        models[h] = {"mu": round(mu, 2), "n": n, "tau": round(sd / math.sqrt(n + SHRINK_GAMES), 2), "avg": round(statistics.mean(xs), 2) if xs else None,
                     "last3": [round(x, 2) for x in xs[-3:]]}
    return models, sd


def _bracket(seeds, draw):
    """seeds: list of handles best first. Returns champion. Sleeper default, no reseeding.

    draw(handle, round) scores one team in one round (0 = the first playoff
    week), so a team can be rated differently from week to week. The games are
    played in the same order as before, which keeps the random stream, and so
    the published numbers, unchanged when every round has the same rating."""
    n = len(seeds)
    def g(a, b, rd):
        return a if draw(a, rd) >= draw(b, rd) else b
    if n == 2:
        return g(seeds[0], seeds[1], 0)
    if n == 4:
        x = g(seeds[0], seeds[3], 0)
        y = g(seeds[1], seeds[2], 0)
        return g(x, y, 1)
    if n == 6:
        a = g(seeds[3], seeds[4], 0)
        x = g(seeds[0], a, 1)
        b = g(seeds[2], seeds[5], 0)
        y = g(seeds[1], b, 1)
        return g(x, y, 2)
    if n == 8:
        a = g(seeds[0], seeds[7], 0)
        b = g(seeds[3], seeds[4], 0)
        x = g(a, b, 1)
        c = g(seeds[1], seeds[6], 0)
        d = g(seeds[2], seeds[5], 0)
        y = g(c, d, 1)
        return g(x, y, 2)
    return seeds[0]


def _toilet(seeds, draw):
    """Sleeper's losers bracket. seeds: the teams that missed the playoffs, worst
    first (the worst teams get the byes). In each game the LOSER advances, so the
    team left at the end is the loser of the losers bracket. Checked against the
    FL Players 2023-2025 brackets: byes and loser-advances match all three (2025:
    Wallner, who has board duty in 2026); the round-one pairings match 2023 and
    2024, while 2025 crossed them over (worst team met the 3rd/6th winner), which
    barely moves the odds."""
    def g(a, b):
        return a if draw(a) < draw(b) else b
    n = len(seeds)
    if n == 2:
        return g(seeds[0], seeds[1])
    if n == 4:
        return g(g(seeds[0], seeds[3]), g(seeds[1], seeds[2]))
    if n == 6:
        return g(g(seeds[0], g(seeds[3], seeds[4])), g(seeds[1], g(seeds[2], seeds[5])))
    if n == 8:
        return g(g(g(seeds[0], seeds[7]), g(seeds[3], seeds[4])), g(g(seeds[1], seeds[6]), g(seeds[2], seeds[5])))
    return seeds[0] if seeds else None


def _seed(teams, wins, pf, div):
    """Seed order. With divisions, each division winner (best record, then points)
    takes a top seed, ordered among themselves; everyone else follows by record."""
    key = lambda h: (-wins[h], -pf[h])
    if not div or len(set(div.values())) < 2:
        return sorted(teams, key=key)
    leaders = []
    for d in sorted(set(div.values())):
        mem = [h for h in teams if div.get(h) == d]
        if mem:
            leaders.append(min(mem, key=key))
    leaders.sort(key=key)
    return leaders + sorted([h for h in teams if h not in leaders], key=key)


ROSTER_WEIGHT = 0.5      # share of a team's rating that comes from its current roster
# First (season, completed week) the roster half applies. T.J., 2026-11-12: it
# switches on with the week 10 results, so the week 9 numbers already quoted in
# that week's newsletters stay as they were.
ROSTER_FROM = (2026, 10)


def _roster_weeks(ctx, teams, weeks, lg_cur):
    """{handle: {week: expected score from the CURRENT roster}} (T.J., 2026-11-12).

    The best legal lineup each week on Sleeper's weekly projections, scored the
    league's way: the measure power.py calls "rest of season", kept per week.
    Projections move with each player's NFL opponent, bye and injury status, so
    this is what lets the odds see rosters, injuries, trades and the NFL
    schedule. Each week is re-centred on the league's real scoring average, so
    only the gap between teams carries over, not the projections' overall level
    or a bye-heavy week. A week with no projections is left out and the caller
    falls back to scoring alone.
    """
    import insights as I
    import power as P
    S, season = ctx["cur"], ctx["season"]
    score = I._scorer(S.league.get("scoring_settings"))
    slots = [s for s in (S.league.get("roster_positions") or []) if s in P.ELIG]
    pos_of = lambda pid: S.pinfo(pid)["pos"]
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "league_page_projections")
    rosters = {S.handle.get(r["roster_id"]): [x for x in (r.get("players") or []) if x]
               for r in S.rosters if S.handle.get(r["roster_id"])}
    out = {h: {} for h in teams}
    for w in weeks:
        try:
            proj = I._projections(season, w, cache_dir, ctx["read_json"], ctx["write_json"], final=False)
        except Exception as e:
            print("odds: projections unavailable for week", w, e)
            continue
        if not proj:
            continue
        got = {}
        for h in teams:
            players = rosters.get(h) or []
            pts = {x: (score(proj.get(x)) or 0) for x in players}
            got[h] = P._best_lineup(slots, players, pts, pos_of)
        if not any(got.values()):
            continue
        m = statistics.mean(got.values())
        for h in teams:
            out[h][w] = lg_cur + (got[h] - m)
    return out


def build_odds_and_previews(ctx):
    cur, season, state = ctx["cur"], ctx["season"], ctx["state"]
    st = cur.league.get("settings") or {}
    n_playoff = st.get("playoff_teams") or 6
    pstart = cur.playoff_start
    median = bool(st.get("league_average_match"))
    done = cur.completed_weeks(state)
    last_done = max(done) if done else 0
    models, sd = team_models(ctx)
    teams = list(models)
    div = {}
    if (st.get("divisions") or 0) > 1:
        for r in getattr(cur, "rosters", []) or []:
            d = (r.get("settings") or {}).get("division")
            h = cur.handle.get(r.get("roster_id"))
            if d and h in models:
                div[h] = d

    rec = {h: [0, 0, 0.0] for h in teams}
    for s, w, _e, a, pa, b, pb, playoff, _l in ctx["history"]["games"]:
        if s != season or playoff:
            continue
        for me, mp, op in ((a, pa, pb), (b, pb, pa)):
            if me in rec:
                rec[me][0] += mp > op
                rec[me][1] += mp < op
                rec[me][2] += mp
    if median:
        for w in done:
            if w >= pstart:
                continue
            wk = [(h, p) for g in ctx["history"]["games"] if g[0] == season and g[1] == w and not g[7]
                  for h, p in ((g[3], g[4]), (g[5], g[6]))]
            if wk:
                med = statistics.median(p for _, p in wk)
                for h, p in wk:
                    if h in rec:
                        rec[h][0] += p > med
                        rec[h][1] += p < med

    schedule = {w: [(cur.handle[a["roster_id"]], cur.handle[b["roster_id"]]) for a, b in cur.pairs(w)]
                for w in range(last_done + 1, pstart)}
    schedule = {w: v for w, v in schedule.items() if v}

    # Roster-aware ratings (T.J., 2026-11-12): one per remaining week and one for
    # the playoff weeks, each half scoring so far and half the current roster's
    # projections. Scoring alone could not see an injury, a trade or the NFL
    # schedule until the points showed up.
    avgs = [m["avg"] for m in models.values() if m["avg"] is not None]
    lg_cur = statistics.mean(avgs) if avgs else statistics.mean(m["mu"] for m in models.values())
    po_weeks = list(range(pstart, 18))
    rw = {h: {} for h in teams}
    if (season, last_done) >= ROSTER_FROM:
        try:
            rw = _roster_weeks(ctx, teams, sorted(schedule) + po_weeks, lg_cur)
        except Exception as e:
            print("odds: roster ratings failed, using scoring alone:", e)
            rw = {h: {} for h in teams}
    base_mu = {h: models[h]["mu"] for h in teams}

    def rating(h, weeks):
        xs = [rw[h][w] for w in weeks if w in rw[h]]
        return base_mu[h] if not xs else (1 - ROSTER_WEIGHT) * base_mu[h] + ROSTER_WEIGHT * statistics.mean(xs)

    mu_week = {h: {w: rating(h, [w]) for w in schedule} for h in teams}
    mu_po = {h: rating(h, po_weeks) for h in teams}
    # one rating per playoff round: the roster's projections for that week
    mu_round = {h: [rating(h, [pstart + k]) for k in range(3)] for h in teams}
    roster_on = any(rw[h] for h in teams)
    for h in teams:
        reg = [rw[h][w] for w in schedule if w in rw[h]]
        models[h]["mu_scores"] = base_mu[h]
        models[h]["mu_roster"] = round(statistics.mean(reg), 2) if reg else None
        models[h]["mu"] = round(rating(h, sorted(schedule)) if schedule else mu_po[h], 2)

    tally = {h: Counter() for h in teams}
    wins_sum = defaultdict(float)
    rnd = random.Random(season * 100 + last_done)
    for _ in range(SIMS):
        # how good each team really is is itself uncertain, most of all early in the season
        off = {h: rnd.gauss(0, models[h]["tau"]) for h in teams}
        wins = {h: rec[h][0] for h in teams}
        pf = {h: rec[h][2] for h in teams}
        for w, pairs in schedule.items():
            scores = {}
            for a, b in pairs:
                sa, sb = rnd.gauss(mu_week[a][w] + off[a], sd), rnd.gauss(mu_week[b][w] + off[b], sd)
                scores[a], scores[b] = sa, sb
                wins[a if sa > sb else b] += 1
            if median and scores:
                med = statistics.median(scores.values())
                for h, s in scores.items():
                    wins[h] += s > med
            for h, s in scores.items():
                pf[h] += s
        order = _seed(teams, wins, pf, div)
        if div:
            for d in set(div.values()):
                mem = [h for h in teams if div.get(h) == d]
                tally[min(mem, key=lambda h: (-wins[h], -pf[h]))]["div"] += 1
        for i, h in enumerate(order):
            wins_sum[h] += wins[h]
            if i < n_playoff:
                tally[h]["playoff"] += 1
            if i < 2 and n_playoff >= 6:
                tally[h]["bye"] += 1
            if i == 0:
                tally[h]["seed1"] += 1
            if i == len(order) - 1:
                tally[h]["last"] += 1
        draw = lambda h, rd=None: rnd.gauss((mu_po[h] if rd is None else mu_round[h][min(rd, 2)]) + off[h], sd)
        champ = _bracket(order[:n_playoff], draw)
        tally[champ]["title"] += 1
        board = _toilet(order[n_playoff:][::-1], draw)
        if board:
            tally[board]["board"] += 1

    # schedule strength: how strong the opponents have been, and how strong the rest look
    faced = defaultdict(list)
    for s_, w, _e, a, pa, b, pb, playoff, _l in ctx["history"]["games"]:
        if s_ != season or playoff:
            continue
        faced[a].append(b)
        faced[b].append(a)
    avg_of = {h: (models[h]["avg"] if models[h]["avg"] is not None else models[h]["mu"]) for h in teams}
    remaining_opp = defaultdict(list)
    for w, pairs in schedule.items():
        for a, b in pairs:
            remaining_opp[a].append(b)
            remaining_opp[b].append(a)
    sos = {}
    for h in teams:
        f = [avg_of[o] for o in faced[h] if o in avg_of]
        r = [models[o]["mu"] for o in remaining_opp[h] if o in models]
        sos[h] = {"faced": round(sum(f) / len(f), 2) if f else None,
                  "rest": round(sum(r) / len(r), 2) if r else None,
                  "opponents": remaining_opp[h]}

    pct = lambda h, k: round(100.0 * tally[h][k] / SIMS, 1)
    rows = [{"h": h, "w": rec[h][0], "l": rec[h][1], "pf": round(rec[h][2], 2), "mu": models[h]["mu"],
             "proj_w": round(wins_sum[h] / SIMS, 1), "playoff": pct(h, "playoff"), "bye": pct(h, "bye"),
             "seed1": pct(h, "seed1"), "title": pct(h, "title"), "last": pct(h, "last"), "board": pct(h, "board"),
             "div": div.get(h), "div_win": pct(h, "div") if div else None,
             "sos_faced": sos[h]["faced"], "sos_rest": sos[h]["rest"], "rest_opponents": sos[h]["opponents"],
             "tau": round(models[h]["tau"], 3),
             "mu_scores": models[h]["mu_scores"], "mu_roster": models[h]["mu_roster"],
             "mu_playoff": round(mu_po[h], 2),
             "mu_weeks": {str(w): round(v, 2) for w, v in sorted(mu_week[h].items())}} for h in teams]
    rows.sort(key=lambda r: (-r["playoff"], -r["title"], -r["proj_w"]))

    path = os.path.join(ctx["data"], "odds.json")
    old = ctx["read_json"](path, {}) or {}
    hist = old.get("history", {}) if old.get("season") == season else {}
    hist[str(last_done)] = {r["h"]: r["playoff"] for r in rows}
    odds = {"generated": now(), "season": season, "through_week": last_done, "sims": SIMS,
            "prior": ("last_season" if (ctx["dynasty"] if ctx.get("odds_prior") is None else ctx["odds_prior"] == "last_season") else "current_season_only"),
            "playoff_teams": n_playoff, "playoff_start": pstart, "median": median, "sd": round(sd, 1),
            "remaining_weeks": sorted(schedule), "teams": rows, "history": hist,
            # the games still to play, so the what-if page can re-run the model in the browser
            "schedule": {str(w): [[a, b] for a, b in pairs] for w, pairs in sorted(schedule.items())},
            "bye_teams": n_playoff - 4 if n_playoff > 4 else 0,
            # division per team; empty when the league has none. Division winners seed first.
            "divisions": div,
            # 0 when no projections could be read and the ratings are scoring alone
            "roster_weight": ROSTER_WEIGHT if roster_on else 0}
    ctx["write_json"](path, odds)

    # previews for the next week
    nxt = last_done + 1
    pairs = [(cur.handle[a["roster_id"]], cur.handle[b["roster_id"]]) for a, b in cur.pairs(nxt)] if nxt <= 18 else []
    games = ctx["history"]["games"]
    previews = []
    for a, b in pairs:
        if a not in models or b not in models:
            continue
        meet = [g for g in games if {g[3], g[5]} == {a, b}]
        wa = sum(1 for g in meet if (g[4] > g[6]) == (g[3] == a) and g[4] != g[6])
        wb = sum(1 for g in meet if g[4] != g[6]) - wa
        streak = None
        for g in reversed(meet):
            if g[4] == g[6]:
                break
            win = g[3] if g[4] > g[6] else g[5]
            if streak is None:
                streak = [win, 1]
            elif win == streak[0]:
                streak[1] += 1
            else:
                break
        last = meet[-1] if meet else None
        spread = math.sqrt(2 * sd * sd + models[a]["tau"] ** 2 + models[b]["tau"] ** 2)
        ma, mb = mu_week[a].get(nxt, models[a]["mu"]), mu_week[b].get(nxt, models[b]["mu"])
        pa_win = round(100 * _phi((ma - mb) / spread), 1)
        flags = []
        if not meet:
            flags.append("First ever meeting")
        if streak and streak[1] >= 3:
            flags.append(f"{{{streak[0]}}} has won {streak[1]} straight in this series")
        finals = [g for g in meet if g[8] == "Championship"]
        for g in finals[-2:]:
            flags.append(f"Rematch of the {g[0]} final")
        if last and last[7] and last[8] in REAL and last[8] != "Championship":
            loser = last[5] if last[4] > last[6] else last[3]
            flags.append(f"Playoff rematch: {{{loser}}} lost the {last[0]} {last[8].lower()}")
        elif last and last[0] == season:
            loser = last[5] if last[4] > last[6] else last[3]
            flags.append(f"Revenge game: {{{loser}}} lost in week {last[1]}")
        if len(meet) >= 6 and max(wa, wb) / max(1, wa + wb) >= 0.7:
            top = a if wa > wb else b
            flags.append(f"{{{top}}} owns this series {max(wa, wb)}-{min(wa, wb)}")
        ra, rb = rec[a], rec[b]
        if nxt > 2 and ra[1] == 0 and rb[1] == 0:
            flags.append("Battle of the unbeatens")
        if nxt > 2 and ra[0] == 0 and rb[0] == 0:
            flags.append("Someone finally gets a win")
        if min(pa_win, 100 - pa_win) <= 30:
            dog = a if pa_win < 50 else b
            flags.append(f"Upset watch: {{{dog}}} is the underdog")
        previews.append({
            "a": a, "b": b, "a_win": pa_win,
            "rec": {a: ra[:2], b: rb[:2]},
            "avg": {a: models[a]["avg"], b: models[b]["avg"]},
            "last3": {a: models[a]["last3"], b: models[b]["last3"]},
            "proj": {a: round(ma, 2), b: round(mb, 2)},
            "h2h": {a: wa, b: wb, "games": len(meet)},
            "streak": streak,
            "last": ({"season": last[0], "week": last[1], "label": last[8],
                      "score": {last[3]: last[4], last[5]: last[6]}} if last else None),
            "flags": flags,
        })
    previews.sort(key=lambda p: -len(p["flags"]))

    # Hand-written copy lives in notes_extra.json and is never overwritten here:
    #   {"<season>": {"<week>": {"league": "...", "byline": "...",
    #                            "games": {"<handleA>--<handleB>": "..."}}}}
    # Game keys are the two handles sorted and joined with "--".
    extra = (ctx["read_json"](os.path.join(ctx["data"], "notes_extra.json"), {}) or {})
    wk_notes = ((extra.get(str(season)) or {}).get(str(nxt)) or {}) if nxt else {}
    game_notes = wk_notes.get("games") or {}
    for p in previews:
        key = "--".join(sorted([p["a"], p["b"]]))
        if game_notes.get(key):
            p["note"] = game_notes[key]

    pv = {"generated": now(), "season": season, "week": nxt if pairs else None,
          "playoff": bool(pairs) and nxt >= pstart, "games": previews,
          "league_note": wk_notes.get("league") or "",
          "byline": wk_notes.get("byline") or "",
          "note": "Win chances use each team's scoring this season, pulled toward last season while the sample is small."}
    ctx["write_json"](os.path.join(ctx["data"], "previews.json"), pv)
    return odds, pv


# ---------------------------------------------------------------- player hall of fame
# Rules T.J. approved 2026-11-15. An All-League season is a top finish at the
# position in points scored while in a lineup in THIS league. The cut-offs per
# league live in site_config.json ("hof"), so a league growing older never
# throws anyone out of the Hall.
HOF_TOP = {"QB": 3, "RB": 6, "WR": 6, "TE": 3, "K": 1, "DEF": 1}
HOF_MIN_STARTS = 8        # starts in a season before it can be All-League
HOF_RING_STARTS = 6       # starts for the champion before the ring counts
WASTE_POS = ("QB", "RB", "WR", "TE")
WASTE_BENCH_WEEKS = 4     # weeks on a bench in a difference-making season
WASTE_BENCH_SHARE = 0.25  # and at least this share of his points scored there
WASTE_MIN_SEASONS = 2     # prime years, plural: one bad landing spot is not a wasted prime


def _hof_cutoffs(ctx, n):
    d = {"peak": 3 if n <= 5 else 4 if n <= 9 else 5, "rings": 2,
         "champ_al": 2 if n <= 5 else 3, "best": 2 if n <= 5 else 3}
    d.update(ctx.get("hof") or {})
    return d


def build_player_hof(ctx, pdata):
    cur = ctx["season"]
    champs, playoff, rec = {}, defaultdict(set), defaultdict(lambda: [0, 0])
    for s, _w, _era, a, pa, b, pb, _po, label in ctx["history"]["games"]:
        if label in REAL:
            playoff[s].add(a)
            playoff[s].add(b)
            if label == "Championship" and pa != pb:
                champs[s] = a if pa > pb else b
        elif not label and pa is not None and pb is not None and (pa or pb):
            if pa > pb:
                rec[(s, a)][0] += 1; rec[(s, b)][1] += 1
            elif pb > pa:
                rec[(s, b)][0] += 1; rec[(s, a)][1] += 1
    players = pdata["players"]
    st_pts, st_n, all_pts, wk_n, bench_pts = (defaultdict(float), defaultdict(int), defaultdict(float),
                                              defaultdict(int), defaultdict(float))
    for p in players:
        for s, _h, pts, st, wk, bn in p["s"]:
            key = (s, p["k"])
            st_pts[key] += pts; st_n[key] += st; wk_n[key] += wk
            bench_pts[key] += bn; all_pts[key] += pts + bn
    pos = {p["k"]: p["p"] for p in players}

    def ranks(table):
        by, out = defaultdict(list), {}
        for (s, k), v in table.items():
            by[(s, pos.get(k, ""))].append((v, k))
        for (s, _po), lst in by.items():
            lst.sort(reverse=True)
            for i, (_v, k) in enumerate(lst):
                out[(s, k)] = i + 1
        return out
    r_st, r_all = ranks(st_pts), ranks(all_pts)
    seasons = sorted({s for s, _ in st_pts if s < cur})
    cut = _hof_cutoffs(ctx, len(seasons))
    bench_from = pdata.get("bench_from") or cur

    inductees, near, wasted = [], [], []
    for p in players:
        k, po = p["k"], p["p"]
        if po not in HOF_TOP:
            continue
        yrs = sorted({r[0] for r in p["s"]})
        al = [s for s in yrs if s < cur and r_st.get((s, k), 99) <= HOF_TOP[po] and st_n[(s, k)] >= HOF_MIN_STARTS]
        no1 = [s for s in al if r_st[(s, k)] == 1]
        rings = sorted({s for s, h, _pts, st, _wk, _bn in p["s"] if champs.get(s) == h and st >= HOF_RING_STARTS})
        via = []
        if len(al) >= cut["peak"]:
            via.append("peak")
        if len(rings) >= cut["rings"] and len(al) >= cut["champ_al"]:
            via.append("champion")
        if len(no1) >= cut["best"]:
            via.append("best")
        by_mgr = defaultdict(float)
        for _s, h, pts, _st, _wk, _bn in p["s"]:
            by_mgr[h] += pts
        card = {"k": k, "n": p["n"], "p": po, "id": p.get("id"), "al": al, "no1": no1, "rings": rings,
                "st": p["st"], "pts": p["pts"], "first": yrs[0], "last": yrs[-1],
                "mgrs": len(by_mgr), "top": max(by_mgr, key=by_mgr.get)}
        if via:
            card["via"] = via
            inductees.append(card)
        elif len(al) == cut["peak"] - 1 and len(al) >= 2:
            near.append(card)
        if po not in WASTE_POS:
            continue
        # prime years wasted: finished seasons where he was a difference maker
        # (top of his position on all points, bench included) for a losing team
        # that missed the playoffs, or while sitting on a bench
        prime, lost = 0, []
        for s in yrs:
            key = (s, k)
            if s >= cur or r_all.get(key, 99) > HOF_TOP[po] or wk_n[key] < HOF_MIN_STARTS:
                continue
            prime += 1
            rows = [r for r in p["s"] if r[0] == s]
            main = max(rows, key=lambda r: r[4])[1]
            w, l = rec.get((s, main), [0, 0])
            bw = wk_n[key] - st_n[key]
            on_bench = (s >= bench_from and bw >= WASTE_BENCH_WEEKS
                        and bench_pts[key] >= WASTE_BENCH_SHARE * all_pts[key])
            on_loser = w < l and main not in playoff.get(s, ())
            if on_bench or on_loser:
                lost.append({"season": s, "h": main, "rank": r_all[key], "total": round(all_pts[key], 1),
                             "w": w, "l": l, "loser": on_loser, "benched": on_bench,
                             "bench": round(bench_pts[key], 1), "bw": bw})
        # at least two such seasons, and at least half of his prime
        # ... and not a player who won two titles here anyway
        if len(lost) >= WASTE_MIN_SEASONS and 2 * len(lost) >= prime and len(rings) < 2:
            wasted.append({"k": k, "n": p["n"], "p": po, "id": p.get("id"), "prime": prime,
                           "rings": len(rings), "seasons": lost})
    inductees.sort(key=lambda c: (-len(c["al"]), -len(c["rings"]), -c["pts"]))
    near.sort(key=lambda c: (-len(c["al"]), -c["pts"]))
    wasted.sort(key=lambda x: (-len(x["seasons"]), x["rings"], sum(y["rank"] for y in x["seasons"])))
    data = {
        "generated": now(), "season": cur, "seasons": len(seasons),
        "first_season": seasons[0] if seasons else cur,
        "missing": (ctx["history"].get("site") or {}).get("missing_seasons") or [],
        "bench_from": bench_from,
        "rules": dict(cut, top=HOF_TOP, min_starts=HOF_MIN_STARTS, ring_starts=HOF_RING_STARTS,
                      bench_weeks=WASTE_BENCH_WEEKS, bench_share=WASTE_BENCH_SHARE,
                      waste_seasons=WASTE_MIN_SEASONS),
        "inductees": inductees, "near": near, "wasted": wasted,
    }
    ctx["write_json"](os.path.join(ctx["static"], "player_hof.json"), data, compact=True)
    return data


# ---------------------------------------------------------------- football stats
# Real football numbers from each manager's starters (T.J., 2026-11-13). Sleeper's
# weekly stat lines only reach back as far as the league has been on Sleeper.
FB_URL = "https://api.sleeper.app/stats/nfl/{season}/{week}?season_type=regular"
FB_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "league_page_stats")
FB_KEYS = ("pass_yd", "pass_td", "pass_int", "rush_yd", "rush_td", "rec", "rec_yd", "rec_td", "fum_lost", "fgm")
FB_LONG = ("pass_lng", "rush_lng", "rec_lng", "fgm_lng")
FB_GAMES = ("pass_yd", "rush_yd", "rec_yd", "rec", "td")


def _fb_week(season, week, fresh):
    """pid -> the stat keys we keep, for one NFL week. Finished weeks are cached on disk."""
    fp = os.path.join(FB_CACHE, "%d-%02d.json" % (season, week))
    if not fresh and os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    import urllib.request
    req = urllib.request.Request(FB_URL.format(season=season, week=week), headers={"User-Agent": "league-page-updater"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.loads(r.read().decode("utf-8"))
    out = {}
    for row in raw if isinstance(raw, list) else []:
        st = row.get("stats") or {}
        keep = {k: st[k] for k in FB_KEYS + FB_LONG if st.get(k)}
        if keep:
            out[str(row.get("player_id"))] = keep
    os.makedirs(FB_CACHE, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def _fb_season(S, weeks, live):
    """One season's totals per manager, plus its biggest games and longest plays."""
    rows = defaultdict(lambda: {k: 0 for k in FB_KEYS})
    games, plays = {k: [] for k in FB_GAMES}, {k: [] for k in FB_LONG}
    through, missing = None, 0
    for w in weeks:
        try:
            st = _fb_week(S.season, w, live and w >= weeks[-1] - 1)   # stat corrections land late
        except Exception as e:
            print("football: no stats for %s week %s: %s" % (S.season, w, e))
            missing += 1
            continue
        through = [S.season, w]
        for m in S.matchups(w):
            h = S.handle.get(m.get("roster_id"))
            if not h:
                continue
            for pid in m.get("starters") or []:
                line = st.get(str(pid))
                if not line:
                    continue
                for k in FB_KEYS:
                    if line.get(k):
                        rows[h][k] += line[k]
                info = S.pinfo(str(pid))
                tag = [info["name"], info["pos"], str(pid), h, S.season, w]
                td = (line.get("pass_td") or 0) + (line.get("rush_td") or 0) + (line.get("rec_td") or 0)
                for k in FB_GAMES:
                    v = td if k == "td" else (line.get(k) or 0)
                    if v:
                        games[k].append([v] + tag)
                for k in FB_LONG:
                    if line.get(k):
                        plays[k].append([line[k]] + tag)
    top = lambda lst, n: sorted(lst, key=lambda x: (-x[0], x[5], x[6]))[:n]
    return {"season": S.season, "rows": {h: dict(v) for h, v in rows.items()}, "through": through, "missing": missing,
            "games": {k: top(v, 10) for k, v in games.items()}, "plays": {k: top(v, 8) for k, v in plays.items()}}


def _fb_past_vault(ctx):
    """In vault mode the build reads only the current season live, so walk back through
    Sleeper here. A finished season never changes: it is read once and kept on disk."""
    cur, out = ctx["cur"], []
    by_user = {cur.owner[rid]: h for rid, h in cur.handle.items() if rid in cur.owner}
    prev = cur.league.get("previous_league_id")
    while prev and prev != "0":
        fp = os.path.join(FB_CACHE, "season-%s.json" % prev)
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as f:
                agg = json.load(f)
        else:
            S = type(cur)(prev, by_user)
            agg = _fb_season(S, S.completed_weeks(ctx["state"]), False)
            agg["prev"] = S.league.get("previous_league_id")
            if not agg["missing"]:
                os.makedirs(FB_CACHE, exist_ok=True)
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(agg, f)
            print("  football: %s read from Sleeper" % agg["season"])
        out.append(agg)
        prev = agg.get("prev")
    return out


def build_football(ctx):
    cur, state = ctx["season"], ctx["state"]
    parts = _fb_past_vault(ctx) if ctx["mode"] == "vault" else []
    for S in ctx["live_seasons"]:
        weeks = S.completed_weeks(state)
        if weeks:
            parts.append(_fb_season(S, weeks, S.season == cur))
    parts.sort(key=lambda a: a["season"])
    mgr = defaultdict(lambda: {"tot": {k: 0 for k in FB_KEYS}, "seasons": {}})
    games, plays = {k: [] for k in FB_GAMES}, {k: [] for k in FB_LONG}
    for a in parts:
        for h, row in a["rows"].items():
            mgr[h]["seasons"][str(a["season"])] = row
            for k in FB_KEYS:
                mgr[h]["tot"][k] += row.get(k, 0)
        for k in FB_GAMES:
            games[k] += a["games"][k]
        for k in FB_LONG:
            plays[k] += a["plays"][k]
    top = lambda lst, n: sorted(lst, key=lambda x: (-x[0], x[5], x[6]))[:n]
    r0 = lambda d: {k: int(round(v)) for k, v in d.items()}
    data = {
        "generated": now(), "seasons": [a["season"] for a in parts],
        "through": parts[-1]["through"] if parts else None, "weeks_missing": sum(a["missing"] for a in parts),
        "managers": {h: {"tot": r0(v["tot"]), "seasons": {s: r0(x) for s, x in v["seasons"].items()}} for h, v in mgr.items()},
        "games": {k: top(v, 10) for k, v in games.items()},
        "plays": {k: top(v, 8) for k, v in plays.items()},
    }
    ctx["write_json"](os.path.join(ctx["static"], "football.json"), data, compact=True)
    return data


def build_all(ctx):
    out = {}
    if ctx["mode"] == "vault":
        sys.path.insert(0, ctx["vault_manual"])
        import flp
        ctx["flp_slots"] = list(flp.slots())
    os.makedirs(ctx["static"], exist_ok=True)
    rows = collect_slots(ctx)
    pdata = build_players(ctx, rows)
    out["players"] = len(pdata["players"])
    try:
        out["hof"] = len(build_player_hof(ctx, pdata)["inductees"])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("player hall of fame failed:", e)
    try:
        fb = build_football(ctx)
        out["football_through"] = fb["through"]
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("football stats failed:", e)
    costly = build_costly(ctx, rows)
    trades = build_trades(ctx, rows)
    out["trades"] = len(trades["trades"])
    drafts = build_drafts(ctx, rows)
    out["picks"] = len(drafts["picks"])
    odds, pv = build_odds_and_previews(ctx)
    out["odds_through"] = odds["through_week"]
    out["previews"] = len(pv["games"])

    import awards as A
    wv = A.build_waivers(ctx, rows, drafts["picks"])
    out["pickups"] = wv["count"]
    out["costly"] = costly["count"]
    aw = A.build_awards(ctx, ctx["history"], trades, drafts, wv)
    out["awards"] = len(aw["awards"])

    import rosters as R
    rs = R.build_rosters(ctx, rows, drafts, trades, wv)
    out["rosters"] = len(rs["managers"])

    # projected vs actual and position-group surprises (insights.py);
    # a failure here must not stop the rest of the Tuesday refresh
    try:
        import insights as I
        ins = I.build_insights(ctx)
        out["insights_through"] = ins.get("through_week")
    except Exception as e:
        print("insights failed:", e)
    try:
        out["trending"] = len(I.build_trending(ctx)["add"])
    except Exception as e:
        print("trending failed:", e)
    # power rankings (power.py): projections, scoring and all-play, built here
    # instead of in the visitor's browser
    try:
        import power as P
        pw = P.build_power(ctx)
        out["power_weeks_left"] = pw["weeks_left"]
    except Exception as e:
        print("power failed:", e)
    # the week's NFL headlines tied to this league (nfl_news.py), for the newsletter
    try:
        import nfl_news as NN
        news = NN.build_nfl_news(ctx)
        out["nfl_news"] = len(news["items"])
        # and tie those headlines to the matchups they touch, for the preview
        # page and the newsletter. previews.json is already written by here.
        out["nfl_previews"] = NN.attach_to_previews(ctx, news)
    except Exception as e:
        print("nfl_news failed:", e)
    # season storylines and trackers (trackers.py), for the /trackers page
    try:
        import trackers as TR
        tr = TR.build_trackers(ctx, drafts, wv)
        out["trackers"] = sum(len(g["cards"]) for g in tr["groups"])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("trackers failed:", e)
    # records within reach, records broken, career milestones (record_watch.py)
    try:
        import record_watch as RW
        out["record_lines"] = len(RW.build_record_watch(ctx)["lines"])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("record watch failed:", e)
    # players who bounce between rosters and land in losses (grenades.py)
    try:
        import grenades as GR
        out["grenades"] = len(GR.run(ctx, rows, now())["grenades"])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("grenades failed:", e)
    # the per-season yearbook pages at /season/<year> (seasons.py)
    try:
        import seasons as SE
        out["seasons"] = len(SE.build_seasons(ctx, rows)["seasons"])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("seasons failed:", e)
    return out
