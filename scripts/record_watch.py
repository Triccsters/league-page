"""record_watch.py - records within reach, records already broken, career milestones.

Writes src/lib/data/record_watch.json at every build, from history.json (every
game the league has played) and odds.json (how many regular-season weeks are
left). Nothing is typed in by hand, so it cannot drift.

  records     season and streak records, each with the teams that can still
              reach it this season ("chasers") and what they need
  fresh       single-game marks set this season that rank in the all-time top 5
  milestones  round-number career marks reached this season or reachable by the
              end of it, with the breakdown behind the wins ones
  passing     places changing hands on the career lists
  lines       the same things as one-line items, most urgent first (home page
              strip, manager cards)
  snap        the top lines as they stood each week, kept from build to build,
              so a newsletter issue keeps the box it went out with

Text carries {handle} placeholders; the page swaps in the shown name.
Season totals are regular season only. A record set in a 13-game season is
flagged when this season has 14, and the per-game records sit beside the totals.
A points or per-game record set before the 2018 move to half PPR is flagged too,
since standard scoring, not the team, is why some of those marks sit where they do.
"""
import os
from collections import defaultdict

REAL = {"Quarterfinal", "Semifinal", "Championship"}
TOP_FRESH = 5
SNAP_LINES = 6

# The league moved to half PPR on 2018-07-25. Every season before that scored
# standard, so a points total or a per-game average from 2017 or earlier is not
# on the same footing as one since, and the records that depend on scoring say so.
# This matters most at the bottom of the table: with 2008-2013 in the pool the
# lowest-scoring records would otherwise all be held by standard-scoring seasons
# and read as unreachable, when the cause is the scoring rules, not the team.
HALF_PPR_FROM = 2018
SCORING_KINDS = ("sum", "avg", "lowavg")


def _n(x, d=2):
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}"
    return f"{x:,.{d}f}".rstrip("0").rstrip(".")


def _pl(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s" if not word.endswith("s") else f"{n} {word}es"


def _ord(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def compute(h, odds, prev=None):
    F = h["fields"]
    G = [dict(zip(F, g)) for g in h["games"]]
    site = h["site"]
    cur = int(site["season"])
    mgr = h.get("managers") or {}
    active = list(h.get("current") or [])
    hidden = lambda m: bool((mgr.get(m) or {}).get("hidden"))
    played = [g for g in G if g["pa"] is not None and g["pb"] is not None and (g["pa"] or g["pb"])]
    rows = []
    for g in played:
        for me, pts, opp, op in ((g["a"], g["pa"], g["b"], g["pb"]), (g["b"], g["pb"], g["a"], g["pa"])):
            rows.append({"s": g["season"], "w": g["week"], "m": me, "pts": pts, "opp": opp, "op": op,
                         "po": bool(g["playoff"]), "label": g["label"]})
    rr = sorted([r for r in rows if not r["po"]], key=lambda r: (r["s"], r["w"]))
    now = [r for r in rr if r["s"] == cur]
    doc = {"season": cur, "through_week": 0, "weeks_left": 0, "season_games": 0, "records": [], "fresh": [],
           "milestones": [], "passing": [], "lines": [], "snap": dict((prev or {}).get("snap") or {})}
    if not now:
        return doc
    wk = max(r["w"] for r in now)
    prior_len = {}
    for r in rr:
        if r["s"] < cur:
            prior_len[r["s"]] = max(prior_len.get(r["s"], 0), r["w"])
    total = None
    if odds and odds.get("season") == cur and odds.get("playoff_start"):
        total = int(odds["playoff_start"]) - 1
    if not total:
        total = prior_len[max(prior_len)] if prior_len else wk
    rem = max(0, total - wk)
    doc.update(through_week=wk, weeks_left=rem, season_games=total)

    # ---- season totals -------------------------------------------------
    tot = defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0, "g": 0, "hi": 0})
    for r in rr:
        t = tot[(r["s"], r["m"])]
        t["g"] += 1; t["pf"] += r["pts"]; t["pa"] += r["op"]
        if r["pts"] > r["op"]: t["w"] += 1
        elif r["pts"] < r["op"]: t["l"] += 1
        else: t["t"] += 1
    wkmax = defaultdict(float)
    for r in rr:
        wkmax[(r["s"], r["w"])] = max(wkmax[(r["s"], r["w"])], r["pts"])
    for r in rr:
        if r["pts"] == wkmax[(r["s"], r["w"])]:
            tot[(r["s"], r["m"])]["hi"] += 1
    P = {k: t for k, t in tot.items() if k[0] < cur and t["g"] >= 10}
    C = {k[1]: t for k, t in tot.items() if k[0] == cur and k[1] in active}
    records, lines = [], []

    def holders(f, hi):
        best = (max if hi else min)(f(t) for t in P.values())
        ks = sorted(k for k, t in P.items() if abs(f(t) - best) < 1e-9)
        return best, ks

    def add(rid, title, unit, f, hi, kind, word=None, d=2):
        if not P:
            return
        rec, ks = holders(f, hi)
        s0, m0 = ks[0]
        g0 = P[ks[0]]["g"]
        rtxt = f"{_n(rec, d)} {unit}, {{{m0}}} in {s0}" + (f" (and {len(ks) - 1} more)" if len(ks) > 1 else "")
        notes = []
        if kind in ("count", "lowcount", "sum") and g0 != total:
            notes.append(f"Set in a {g0}-game season; this one has {total}.")
        if kind in SCORING_KINDS and s0 < HALF_PPR_FROM:
            notes.append(f"Set under standard scoring, before the {HALF_PPR_FROM} move to half PPR, "
                         f"so it is not on the same footing as a season since.")
        note = " ".join(notes) or None
        ch, status = [], "safe"
        for m, t in C.items():
            v = f(t); g = t["g"]; txt = None; heat = 0; broke = False
            if kind == "count":
                if v > rec:
                    broke = True; txt = f"Already at {_n(v)}, a new record with {_pl(rem, 'week')} left."
                elif v + rem > rec:
                    txt = f"At {_n(v)} with {rem} to play. {_n(rec - v + 1)} more breaks it, {_n(rec - v)} ties it."; heat = 1 - (rec - v + 1) / (rem + 1)
                elif v + rem == rec and rem:
                    txt = f"At {_n(v)} with {rem} to play. {word.capitalize()} out to tie it."; heat = 0.05
            elif kind == "lowcount":
                if rem and v < rec:
                    txt = f"At {_n(v)} with {rem} to play. {_n(rec - v - 1)} more at most to finish under the record, {_n(rec - v)} to tie." if rec - v - 1 > 0 else f"At {_n(v)} with {rem} to play. One more only ties it; none sets the record."
                    heat = 0.3
                elif rem and v == rec:
                    txt = f"At {_n(v)} with {rem} to play. Stays there the rest of the way to tie it."; heat = 0.1
                elif not rem and v < rec:
                    broke = True; txt = f"Finished at {_n(v)}, a new record."
            elif kind == "sum":
                avg = v / g
                if v > rec:
                    broke = True; txt = f"Already at {_n(v)}, a new record with {_pl(rem, 'week')} left."
                elif rem:
                    need = (rec - v) / rem
                    if need <= avg * 1.15:
                        txt = f"{_n(v)} so far, {_n(avg, 1)} a game. Needs {_n(need, 1)} a game over the last {rem}."; heat = min(1, avg / need) if need > 0 else 1
            elif kind in ("avg", "lowavg"):
                avg = v
                tv = t["pf"] if rid.startswith("ppg") else t["pa"]
                if rem:
                    need = (rec * (g + rem) - tv) / rem
                    if kind == "avg" and need <= avg * 1.15:
                        txt = f"{_n(avg)} a game now. Needs {_n(need, 1)} a game the rest of the way to finish above it."; heat = min(1, avg / need) if need > 0 else 1
                    if kind == "lowavg" and need >= avg * 0.85:
                        txt = f"{_n(avg)} a game now. Finishes under it by averaging less than {_n(need, 1)} the rest of the way."; heat = min(1, need / avg) if avg > 0 else 1
                elif (kind == "avg" and avg > rec) or (kind == "lowavg" and avg < rec):
                    broke = True; txt = f"Finished at {_n(avg)} a game, a new record."
            if txt:
                ch.append({"h": m, "text": txt, "now": round(v, 2), "heat": round(heat, 3), "broke": broke})
        ch.sort(key=lambda c: (-c["broke"], -c["heat"]))
        ch = ch[:4]
        if any(c["broke"] for c in ch): status = "broken"
        elif ch: status = "live"
        records.append({"id": rid, "group": "season", "title": title, "record": rtxt, "holder": m0, "holder_season": s0,
                        "value": round(rec, 2), "note": note, "status": status, "chasers": ch})

    add("wins", "Most wins in a season", "wins", lambda t: t["w"], True, "count", "win")
    add("losses", "Most losses in a season", "losses", lambda t: t["l"], True, "count", "lose")
    add("fewest_wins", "Fewest wins in a season", "wins", lambda t: t["w"], False, "lowcount")
    add("fewest_losses", "Fewest losses in a season", "losses", lambda t: t["l"], False, "lowcount")
    add("points", "Most points in a season", "points", lambda t: t["pf"], True, "sum")
    add("ppg_hi", "Highest scoring average in a season", "a game", lambda t: t["pf"] / t["g"], True, "avg")
    add("ppg_lo", "Lowest scoring average in a season", "a game", lambda t: t["pf"] / t["g"], False, "lowavg")
    add("pa_hi", "Most points against per game", "a game", lambda t: t["pa"] / t["g"], True, "avg")
    add("pa_lo", "Fewest points against per game", "a game", lambda t: t["pa"] / t["g"], False, "lowavg")
    add("weekly_highs", "Most weekly high scores in a season", "weeks on top", lambda t: t["hi"], True, "count", "top the week")
    for r in records:
        if r["id"] == "weekly_highs":
            r["chasers"] = [c for c in r["chasers"] if c["now"] >= 2 or c["broke"]]
            if not r["chasers"]: r["status"] = "safe"

    # ---- streaks (regular season, carried across seasons) --------------
    bym = defaultdict(list)
    for r in rr:
        bym[r["m"]].append(r)
    long_win = {}
    for kind, title, word in (("W", "Longest winning streak", "win"), ("L", "Longest losing streak", "loss")):
        best = (0, None, None, None); live = []
        for m, lst in bym.items():
            run = 0; start = None; mbest = 0
            res_of = lambda r: "W" if r["pts"] > r["op"] else "L" if r["pts"] < r["op"] else "T"
            # a run still going for a current team is a chaser, not the record it chases
            tail = len(lst)
            if m in active and lst[-1]["s"] == cur:
                while tail > 0 and res_of(lst[tail - 1]) == kind: tail -= 1
            for i, r in enumerate(lst):
                if res_of(r) == kind:
                    if run == 0: start = r
                    run += 1
                    mbest = max(mbest, run)
                    if i < tail and run > best[0]:
                        best = (run, m, start, r)
                else:
                    run = 0
            if kind == "W": long_win[m] = mbest
            if m in active and run >= 3 and lst[-1]["s"] == cur:
                live.append((run, m))
        rec = best[0]
        if not rec: continue
        ch = []
        for run, m in sorted(live, reverse=True):
            if run > rec:
                ch.append({"h": m, "text": f"{run} straight and still going, a new record.", "now": run, "heat": 1, "broke": True})
            elif run + rem > rec:
                ch.append({"h": m, "text": f"{run} straight. {rec - run + 1} more breaks it, {rec - run} ties it.", "now": run, "heat": run / rec, "broke": False})
            elif run + rem == rec and rem:
                ch.append({"h": m, "text": f"{run} straight. Can only tie it this season.", "now": run, "heat": 0.05, "broke": False})
        records.append({"id": "streak_" + kind, "group": "streak", "title": title,
                        "record": f"{rec} straight, {{{best[1]}}}, {best[2]['s']} week {best[2]['w']} to {best[3]['s']} week {best[3]['w']}",
                        "holder": best[1], "holder_season": best[3]["s"], "value": rec, "note": None,
                        "status": "broken" if any(c["broke"] for c in ch) else "live" if ch else "safe", "chasers": ch[:4]})

    # ---- single games set this season ----------------------------------
    counted = [r for r in rows if (not r["po"] or r["label"] in REAL) and r["pts"] > 0]
    dec = [r for r in counted if r["pts"] > r["op"]]
    when = lambda r: (r["label"] if r["po"] else f"week {r['w']}")
    fresh = []

    def single(title, pool, key, hi, say):
        ranked = sorted(pool, key=key, reverse=hi)
        for i, r in enumerate(ranked[:TOP_FRESH]):
            if r["s"] == cur:
                fresh.append({"title": title, "rank": i + 1, "h": r["m"], "week": r["w"], "value": round(key(r), 2),
                              "text": say(r) + (", a new league record." if i == 0 else f", {_ord(i + 1)} on the all-time list.")})

    single("Highest score", counted, lambda r: r["pts"], True, lambda r: f"{{{r['m']}}} scored {_n(r['pts'])} in {when(r)}")
    single("Lowest score", counted, lambda r: r["pts"], False, lambda r: f"{{{r['m']}}} scored {_n(r['pts'])} in {when(r)}")
    single("Biggest blowout", dec, lambda r: r["pts"] - r["op"], True, lambda r: f"{{{r['m']}}} beat {{{r['opp']}}} by {_n(r['pts'] - r['op'])} in {when(r)}")
    single("Closest game", dec, lambda r: r["pts"] - r["op"], False, lambda r: f"{{{r['m']}}} beat {{{r['opp']}}} by {_n(r['pts'] - r['op'])} in {when(r)}")
    single("Most points in a loss", [r for r in counted if r["pts"] < r["op"]], lambda r: r["pts"], True, lambda r: f"{{{r['m']}}} scored {_n(r['pts'])} and lost to {{{r['opp']}}} in {when(r)}")
    single("Fewest points in a win", dec, lambda r: r["pts"], False, lambda r: f"{{{r['m']}}} won with {_n(r['pts'])} over {{{r['opp']}}} in {when(r)}")
    single("Highest combined score", dec, lambda r: r["pts"] + r["op"], True, lambda r: f"{{{r['m']}}} and {{{r['opp']}}} combined for {_n(r['pts'] + r['op'])} in {when(r)}")

    # ---- career lists, milestones, places changing hands ----------------
    car = defaultdict(lambda: {"w": 0, "l": 0, "pf": 0.0, "g": 0})
    start = defaultdict(lambda: {"w": 0, "l": 0, "pf": 0.0, "g": 0})
    for r in rr:
        if hidden(r["m"]): continue
        for d in ((car, start) if r["s"] < cur else (car,)):
            c = d[r["m"]]
            c["g"] += 1; c["pf"] += r["pts"]
            if r["pts"] > r["op"]: c["w"] += 1
            elif r["pts"] < r["op"]: c["l"] += 1
    top_pts = max((c["pf"] for c in car.values()), default=0)
    STATS = (("w", "wins", "career wins", 25), ("l", "losses", "career losses", 25),
             ("pf", "points", "career points", 5000 if top_pts > 15000 else 2500), ("g", "games", "games played", 50))
    avgp = {m: t["pf"] / t["g"] for m, t in C.items() if t["g"]}
    milestones, passing = [], []

    def win_detail(m):
        ws = [r for r in bym[m] if r["pts"] > r["op"]]
        if not ws: return None
        by_s = defaultdict(int); beat = defaultdict(int)
        for r in ws:
            by_s[r["s"]] += 1; beat[r["opp"]] += 1
        big = max(ws, key=lambda r: r["pts"] - r["op"]); close = min(ws, key=lambda r: r["pts"] - r["op"])
        g1 = lambda r: {"season": r["s"], "week": r["w"], "opp": r["opp"], "pts": r["pts"], "opts": r["op"], "margin": round(r["pts"] - r["op"], 2)}
        return {"by_season": [[s, by_s[s]] for s in sorted(by_s)],
                "beaten_most": [[o, n] for o, n in sorted(beat.items(), key=lambda x: -x[1])[:3]],
                "biggest": g1(big), "closest": g1(close), "longest_streak": long_win.get(m, 0)}

    for key, word, label, step in STATS:
        order = sorted(car.items(), key=lambda x: -x[1][key])
        rank = {m: i + 1 for i, (m, _) in enumerate(order)}
        for m, c in order:
            if m not in active: continue
            v = c[key]; v0 = start[m][key]
            gain = rem if key != "pf" else rem * avgp.get(m, 0) * 1.1
            base = {"h": m, "stat": word, "label": label, "value": round(v, 2), "rank": rank[m], "of": len(order)}
            if int(v // step) > int(v0 // step) and v0 // step * step + step <= v:
                mark = (int(v0 // step) + 1) * step
                run = v0; game = None
                for r in bym[m]:
                    if r["s"] != cur: continue
                    inc = r["pts"] if key == "pf" else 1 if key == "g" else int(r["pts"] > r["op"]) if key == "w" else int(r["pts"] < r["op"])
                    run += inc
                    if run >= mark:
                        game = {"season": r["s"], "week": r["w"], "opp": r["opp"], "pts": r["pts"], "opts": r["op"]}; break
                ms = dict(base, mark=mark, reached=True, game=game,
                          text=f"{{{m}}} reached {_n(mark)} {label}" + (f" in week {game['week']} against {{{game['opp']}}}" if game else "") + f". {_ord(rank[m])} on the all-time list.")
                if key == "w": ms["detail"] = win_detail(m)
                milestones.append(ms)
            nxt = (int(v // step) + 1) * step
            if rem and v + gain >= nxt:
                away = nxt - v
                ms = dict(base, mark=nxt, reached=False, away=round(away, 2),
                          text=f"{{{m}}} is {_n(away, 1)} away from {_n(nxt)} {label}, with {_pl(rem, 'week')} left.")
                if key == "w": ms["detail"] = win_detail(m)
                milestones.append(ms)
        for i, (m, c) in enumerate(order):
            if m not in active: continue
            v = c[key]
            for x, cx in order:
                if x == m: continue
                if start[x][key] > start[m][key] and v > cx[key] and rank[m] <= 10:
                    passing.append({"h": m, "over": x, "stat": word, "rank": rank[m], "done": True,
                                    "text": f"{{{m}}} passed {{{x}}} this season and is {_ord(rank[m])} in {label} ({_n(v)})."})
            if i == 0 or not rem or i > 10: continue
            x, cx = order[i - 1]
            gap = cx[key] - v
            xa = x in active
            if key == "pf":
                ok = v + rem * avgp.get(m, 0) > cx[key] + (rem * avgp.get(x, 0) if xa else 0)
            else:
                ok = gap <= (min(rem, 2) if xa else rem)
            if key in ("l", "g") and xa: ok = False
            if ok and gap >= 0:
                passing.append({"h": m, "over": x, "stat": word, "rank": i, "done": False, "gap": round(gap, 2),
                                "text": (f"{{{m}}} ({_n(v)}) is tied with {{{x}}} for {_ord(i)} in {label}." if gap == 0 else f"{{{m}}} ({_n(v)}) is {_n(gap, 1)} behind {{{x}}} for {_ord(i)} in {label}.") + (" Both are still playing." if xa else "")})
    milestones.sort(key=lambda x: (not x["reached"], x.get("away", 0) if x["stat"] != "points" else x.get("away", 0) / 100))

    # ---- one-line items, most urgent first ------------------------------
    for r in records:
        for c in r["chasers"]:
            if c["broke"]: lines.append({"k": "broken", "h": c["h"], "holder": r["holder"], "title": r["title"], "text": f"{{{c['h']}}}: {c['text']} The old mark was {r['record']}."})
    for f in sorted(fresh, key=lambda f: (f["rank"], -f["week"])):
        if f["rank"] == 1: lines.append({"k": "fresh", "h": f["h"], "title": f["title"], "text": f["text"], "week": f["week"]})
    for m in milestones:
        if m["reached"] and (m.get("game") or {}).get("week") == wk: lines.append({"k": "milestone", "h": m["h"], "title": f"{_n(m['mark'])} {m['label']}", "text": m["text"], "week": wk})
    for m in milestones:
        if not m["reached"] and m["stat"] in ("wins", "points"): lines.append({"k": "milestone", "h": m["h"], "title": f"{_n(m['mark'])} {m['label']}", "text": m["text"]})
    for r in records:
        if r["group"] == "streak":
            for c in r["chasers"]:
                if not c["broke"]: lines.append({"k": "streak", "h": c["h"], "holder": r["holder"], "title": r["title"], "text": f"{{{c['h']}}}: {c['text']} The record is {r['record']}."})
    for p in passing:
        if not p["done"] and p["stat"] in ("wins", "points") and p["rank"] <= 5: lines.append({"k": "pass", "h": p["h"], "title": f"Career {p['stat']}", "text": p["text"]})
    chase = [(c["heat"], r, c) for r in records if r["group"] == "season" for c in r["chasers"] if not c["broke"]]
    for _, r, c in sorted(chase, key=lambda x: -x[0]):
        lines.append({"k": "chase", "h": c["h"], "holder": r["holder"], "title": r["title"], "text": f"{{{c['h']}}}: {c['text']} The record is {r['record']}."})
    for m in milestones:
        if m["reached"] and (m.get("game") or {}).get("week") != wk: lines.append({"k": "milestone", "h": m["h"], "title": f"{_n(m['mark'])} {m['label']}", "text": m["text"]})
    for f in sorted(fresh, key=lambda f: (f["rank"], -f["week"])):
        if f["rank"] > 1: lines.append({"k": "fresh", "h": f["h"], "title": f["title"], "text": f["text"], "week": f["week"]})
    for p in passing:
        if p["done"]: lines.append({"k": "pass", "h": p["h"], "title": f"Career {p['stat']}", "text": p["text"]})

    doc.update(records=records, fresh=sorted(fresh, key=lambda f: (f["rank"], -f["week"])), milestones=milestones,
               passing=passing, lines=lines)
    doc["snap"][f"{cur}-w{wk:02d}"] = lines[:SNAP_LINES]
    return doc


def build_record_watch(ctx):
    data = ctx["data"]
    h = ctx.get("history")
    if not (isinstance(h, dict) and "games" in h and "fields" in h):
        h = ctx["read_json"](os.path.join(data, "history.json"), None)
    odds = ctx["read_json"](os.path.join(data, "odds.json"), {}) or {}
    fp = os.path.join(data, "record_watch.json")
    doc = compute(h, odds, ctx["read_json"](fp, {}) or {})
    ctx["write_json"](fp, doc)
    return doc


if __name__ == "__main__":      # python record_watch.py <repo folder>: build from the files already there
    import io, json, sys
    data = os.path.join(sys.argv[1], "src", "lib", "data")
    ld = lambda n: json.load(io.open(os.path.join(data, n), encoding="utf-8")) if os.path.exists(os.path.join(data, n)) else {}
    d = compute(ld("history.json"), ld("odds.json"), ld("record_watch.json"))
    io.open(os.path.join(data, "record_watch.json"), "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
    print(sys.argv[1], "through week", d["through_week"], "left", d["weeks_left"], "| records live/broken:",
          [(r["id"], r["status"], len(r["chasers"])) for r in d["records"] if r["status"] != "safe"],
          "| fresh", len(d["fresh"]), "milestones", len(d["milestones"]), "passing", len(d["passing"]), "lines", len(d["lines"]))
    for l in d["lines"][:14]:
        print("   ", l["k"], "|", l["title"], "|", l["text"].encode("ascii", "replace").decode())
