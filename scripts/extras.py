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
def build_players(ctx, rows):
    per = {}
    tops = []
    for season, week, h, k, name, pos, st, pts in rows:
        p = per.setdefault(k, {"n": name, "p": pos, "pts": 0.0, "st": 0, "wk": 0, "s": {}})
        if pos and not p["p"]:
            p["p"] = pos
        if season >= p.get("last", 0):
            p["n"], p["last"] = name, season
        e = p["s"].setdefault((season, h), [0.0, 0, 0])
        e[2] += 1
        p["wk"] += 1
        if st:
            e[0] += pts
            e[1] += 1
            p["pts"] += pts
            p["st"] += 1
            tops.append((pts, season, week, h, name, pos))
    out = []
    for k, p in per.items():
        if p["pts"] < 25 and p["st"] < 3:
            continue
        seasons = sorted(([s, h, round(v[0], 2), v[1], v[2]] for (s, h), v in p["s"].items()),
                         key=lambda x: (x[0], -x[2]))
        out.append({"k": k, "n": p["n"], "p": p["p"], "pts": round(p["pts"], 2), "st": p["st"],
                    "wk": p["wk"], "s": seasons})
    out.sort(key=lambda x: -x["pts"])
    tops.sort(key=lambda x: -x[0])
    data = {
        "generated": now(),
        "first_season": min((r[0] for r in rows), default=ctx["season"]),
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


def build_trades(ctx, rows):
    idx = started_index(rows)
    dyn = ctx["dynasty"]
    trades = []
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
                    picks = [f"{p.get('season')} round {p.get('round')}"
                             for p in (tx.get("draft_picks") or []) if p.get("owner_id") == rid]
                    faab = sum((w.get("amount") or 0) for w in (tx.get("waiver_budget") or []) if w.get("receiver") == rid)
                    if faab:
                        picks.append(f"${faab} FAAB")
                    sides[h] = {"got": got, "picks": picks, "value": round(sum(g["pts"] for g in got), 2)}
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
    base = defaultdict(list)
    for p in picks:
        base[(p[0], p[8], p[1])].append(p[6])
    base = {k: sum(v) / len(v) for k, v in base.items() if v}
    for p in picks:
        p.append(round(p[6] - base.get((p[0], p[8], p[1]), 0), 2))      # index 9: over round average
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
    data = {"generated": now(), "dynasty": dyn,
            "fields": ["season", "round", "pick", "manager", "player", "pos", "value", "live", "draft", "over"],
            "picks": picks, "grades": grades, "managers": managers}
    ctx["write_json"](os.path.join(ctx["static"], "drafts.json"), data, compact=True)
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
    """seeds: list of handles best first. Returns champion. Sleeper default, no reseeding."""
    n = len(seeds)
    def g(a, b):
        return a if draw(a) >= draw(b) else b
    if n == 2:
        return g(seeds[0], seeds[1])
    if n == 4:
        return g(g(seeds[0], seeds[3]), g(seeds[1], seeds[2]))
    if n == 6:
        return g(g(seeds[0], g(seeds[3], seeds[4])), g(seeds[1], g(seeds[2], seeds[5])))
    if n == 8:
        return g(g(g(seeds[0], seeds[7]), g(seeds[3], seeds[4])), g(g(seeds[1], seeds[6]), g(seeds[2], seeds[5])))
    return seeds[0]


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

    tally = {h: Counter() for h in teams}
    wins_sum = defaultdict(float)
    rnd = random.Random(season * 100 + last_done)
    for _ in range(SIMS):
        # how good each team really is is itself uncertain, most of all early in the season
        true_mu = {h: rnd.gauss(models[h]["mu"], models[h]["tau"]) for h in teams}
        wins = {h: rec[h][0] for h in teams}
        pf = {h: rec[h][2] for h in teams}
        for w, pairs in schedule.items():
            scores = {}
            for a, b in pairs:
                sa, sb = rnd.gauss(true_mu[a], sd), rnd.gauss(true_mu[b], sd)
                scores[a], scores[b] = sa, sb
                wins[a if sa > sb else b] += 1
            if median and scores:
                med = statistics.median(scores.values())
                for h, s in scores.items():
                    wins[h] += s > med
            for h, s in scores.items():
                pf[h] += s
        order = sorted(teams, key=lambda h: (-wins[h], -pf[h]))
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
        champ = _bracket(order[:n_playoff], lambda h: rnd.gauss(true_mu[h], sd))
        tally[champ]["title"] += 1

    pct = lambda h, k: round(100.0 * tally[h][k] / SIMS, 1)
    rows = [{"h": h, "w": rec[h][0], "l": rec[h][1], "pf": round(rec[h][2], 2), "mu": models[h]["mu"],
             "proj_w": round(wins_sum[h] / SIMS, 1), "playoff": pct(h, "playoff"), "bye": pct(h, "bye"),
             "seed1": pct(h, "seed1"), "title": pct(h, "title"), "last": pct(h, "last")} for h in teams]
    rows.sort(key=lambda r: (-r["playoff"], -r["title"], -r["proj_w"]))

    path = os.path.join(ctx["data"], "odds.json")
    old = ctx["read_json"](path, {}) or {}
    hist = old.get("history", {}) if old.get("season") == season else {}
    hist[str(last_done)] = {r["h"]: r["playoff"] for r in rows}
    odds = {"generated": now(), "season": season, "through_week": last_done, "sims": SIMS,
            "prior": ("last_season" if (ctx["dynasty"] if ctx.get("odds_prior") is None else ctx["odds_prior"] == "last_season") else "current_season_only"),
            "playoff_teams": n_playoff, "playoff_start": pstart, "median": median, "sd": round(sd, 1),
            "remaining_weeks": sorted(schedule), "teams": rows, "history": hist}
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
        pa_win = round(100 * _phi((models[a]["mu"] - models[b]["mu"]) / spread), 1)
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
            "proj": {a: models[a]["mu"], b: models[b]["mu"]},
            "h2h": {a: wa, b: wb, "games": len(meet)},
            "streak": streak,
            "last": ({"season": last[0], "week": last[1], "label": last[8],
                      "score": {last[3]: last[4], last[5]: last[6]}} if last else None),
            "flags": flags,
        })
    previews.sort(key=lambda p: -len(p["flags"]))
    pv = {"generated": now(), "season": season, "week": nxt if pairs else None,
          "playoff": bool(pairs) and nxt >= pstart, "games": previews,
          "note": "Win chances use each team's scoring this season, pulled toward last season while the sample is small."}
    ctx["write_json"](os.path.join(ctx["data"], "previews.json"), pv)
    return odds, pv


def build_all(ctx):
    out = {}
    if ctx["mode"] == "vault":
        sys.path.insert(0, ctx["vault_manual"])
        import flp
        ctx["flp_slots"] = list(flp.slots())
    os.makedirs(ctx["static"], exist_ok=True)
    rows = collect_slots(ctx)
    out["players"] = len(build_players(ctx, rows)["players"])
    out["trades"] = len(build_trades(ctx, rows)["trades"])
    out["picks"] = len(build_drafts(ctx, rows)["picks"])
    odds, pv = build_odds_and_previews(ctx)
    out["odds_through"] = odds["through_week"]
    out["previews"] = len(pv["games"])
    return out
