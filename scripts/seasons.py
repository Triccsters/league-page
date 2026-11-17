"""seasons.json: one entry per season for the yearbook pages at /season/<year>.

Everything here is computed from history.json, with the draft and trade sections
left to the page (it filters drafts.json and trades.json by year, which are
already built and already fetched elsewhere - no point duplicating 214K).

What each season entry carries:
  format    teams, regular-season weeks, playoff weeks, scoring era, oddities
  standings final regular-season table with seed, points rank and playoff result
  bracket   the playoff games grouped by round, in bracket order
  awards    the season's awards (see AWARDS below)
  champion  winner, runner-up, third, with the title-game score

SEASON AWARDS NEED NO ERA ADJUSTMENT. Every one compares teams inside a single
season, under one scoring system, against the same schedule length. That is the
opposite of the all-time records, where the 2018 move to half PPR means a raw
cross-era comparison is meaningless. Said on the page so nobody adjusts twice.

Unidentified ('?') teams DO win season awards. A team-season stands on its own
whoever held the remote (T.J., 2026-11-16). They are excluded from CAREER lists
only - see build_unclaimed in update_site.py.
"""
import os
from collections import defaultdict

HALF_PPR_FROM = 2018          # scoring moved to half PPR on 2018-07-25
FRACTIONAL_FROM = 2013        # Yahoo kept whole-number scoring before this
REAL_ROUNDS = ("Quarterfinal", "Semifinal", "Championship")


def _r(x, d=2):
    return round(x + 0.0, d)


def scoring_era(season):
    if season >= HALF_PPR_FROM:
        return "half PPR"
    if season >= FRACTIONAL_FROM:
        return "standard, fractional points"
    return "standard, whole points"


def build(history):
    F = {k: i for i, k in enumerate(history["fields"])}
    S, W, E, A, PA, B, PB, PO, LB = (F["season"], F["week"], F["era"], F["a"],
                                     F["pa"], F["b"], F["pb"], F["playoff"], F["label"])
    names = history.get("team_names") or {}
    cur = (history.get("site") or {}).get("season")

    # one row per team per game
    rows = defaultdict(list)
    for g in history["games"]:
        pa, pb = g[PA], g[PB]
        if pa is None or pb is None or not (pa or pb):
            continue
        for me, pts, opp, op in ((g[A], pa, g[B], pb), (g[B], pb, g[A], pa)):
            if not me:
                continue
            rows[g[S]].append(dict(w=g[W], m=me, pts=_r(pts), opp=opp, op=_r(op),
                                   po=bool(g[PO]), label=g[LB], era=g[E]))

    out = {}
    for season in sorted(rows):
        rs = rows[season]
        reg = [r for r in rs if not r["po"]]
        po = [r for r in rs if r["po"]]
        teams = sorted({r["m"] for r in rs})
        tn = names.get(str(season), {})

        # ---- regular-season table -------------------------------------
        tot = {}
        for r in reg:
            t = tot.setdefault(r["m"], dict(h=r["m"], w=0, l=0, t=0, pf=0.0, pa=0.0, g=0))
            t["g"] += 1
            t["pf"] += r["pts"]
            t["pa"] += r["op"]
            if r["pts"] > r["op"]:
                t["w"] += 1
            elif r["pts"] < r["op"]:
                t["l"] += 1
            else:
                t["t"] += 1

        # all-play: record against everyone else that week, for schedule luck
        byweek = defaultdict(list)
        for r in reg:
            byweek[r["w"]].append(r)
        allplay = defaultdict(lambda: [0, 0])
        for wk, lst in byweek.items():
            for r in lst:
                for o in lst:
                    if o["m"] == r["m"]:
                        continue
                    if r["pts"] > o["pts"]:
                        allplay[r["m"]][0] += 1
                    elif r["pts"] < o["pts"]:
                        allplay[r["m"]][1] += 1

        # weeks as the top scorer
        tops = defaultdict(int)
        for wk, lst in byweek.items():
            best = max(r["pts"] for r in lst)
            for r in lst:
                if r["pts"] == best:
                    tops[r["m"]] += 1

        # longest win streak inside the season
        streak = {}
        for m in teams:
            mine = sorted([r for r in reg if r["m"] == m], key=lambda r: r["w"])
            best = run = 0
            for r in mine:
                run = run + 1 if r["pts"] > r["op"] else 0
                best = max(best, run)
            streak[m] = best

        for m, t in tot.items():
            t["pf"] = _r(t["pf"])
            t["pa"] = _r(t["pa"])
            t["pct"] = _r((t["w"] + t["t"] / 2) / t["g"], 4) if t["g"] else 0
            t["ppg"] = _r(t["pf"] / t["g"]) if t["g"] else 0
            ap = allplay[m]
            t["allplay"] = ap
            t["allplay_pct"] = _r(ap[0] / (ap[0] + ap[1]), 4) if (ap[0] + ap[1]) else 0
            t["luck"] = _r(t["pct"] - t["allplay_pct"], 4)
            t["tops"] = tops.get(m, 0)
            t["streak"] = streak.get(m, 0)
            t["name"] = tn.get(m) or m

        table = sorted(tot.values(), key=lambda t: (-t["pct"], -t["pf"]))
        by_pf = sorted(tot.values(), key=lambda t: -t["pf"])
        pf_rank = {t["h"]: i + 1 for i, t in enumerate(by_pf)}
        for i, t in enumerate(table):
            t["seed"] = i + 1
            t["pf_rank"] = pf_rank[t["h"]]

        # ---- playoff bracket ------------------------------------------
        bracket = defaultdict(list)
        seen = set()
        for r in po:
            key = (r["w"], tuple(sorted((r["m"], r["opp"]))))
            if key in seen:
                continue
            seen.add(key)
            won = r["m"] if r["pts"] > r["op"] else (r["opp"] if r["op"] > r["pts"] else None)
            bracket[r["label"] or f"Week {r['w']}"].append(dict(
                week=r["w"], a=r["m"], pa=r["pts"], b=r["opp"], pb=r["op"],
                winner=won,
                aname=tn.get(r["m"]) or r["m"], bname=tn.get(r["opp"]) or r["opp"]))

        final = bracket.get("Championship", [])
        champ = runner = third = None
        title = None
        if final:
            f = final[0]
            champ = f["winner"]
            runner = f["b"] if f["winner"] == f["a"] else f["a"]
            title = f
        t3 = bracket.get("3rd place", [])
        if t3:
            third = t3[0]["winner"]

        # playoff result per team, for the standings table
        result = {}
        for lab, gs in bracket.items():
            for g in gs:
                for side in (g["a"], g["b"]):
                    result.setdefault(side, []).append(lab)
        for t in table:
            t["playoff"] = sorted(set(result.get(t["h"], [])))
        if champ:
            for t in table:
                if t["h"] == champ:
                    t["title"] = True

        # ---- awards ---------------------------------------------------
        aw = []

        def add(key, title_, who, detail, value=None):
            if who:
                aw.append(dict(key=key, title=title_, h=who,
                               name=tn.get(who) or who, detail=detail, value=value))

        if table:
            b = table[0]
            add("record", "Best record", b["h"],
                f"{b['w']}-{b['l']}{'-' + str(b['t']) if b['t'] else ''}", b["pct"])
            p = by_pf[0]
            add("points", "Most points", p["h"], f"{p['pf']} points, {p['ppg']} a game", p["pf"])
            lo = by_pf[-1]
            add("fewest_points", "Fewest points", lo["h"],
                f"{lo['pf']} points, {lo['ppg']} a game", lo["pf"])
            pa_hi = max(table, key=lambda t: t["pa"])
            add("toughest", "Toughest schedule", pa_hi["h"],
                f"{pa_hi['pa']} points against", pa_hi["pa"])
            pa_lo = min(table, key=lambda t: t["pa"])
            add("easiest", "Easiest schedule", pa_lo["h"],
                f"{pa_lo['pa']} points against", pa_lo["pa"])
            lucky = max(table, key=lambda t: t["luck"])
            add("lucky", "Luckiest schedule", lucky["h"],
                f"{lucky['w']}-{lucky['l']} with an all-play record of "
                f"{lucky['allplay'][0]}-{lucky['allplay'][1]}", lucky["luck"])
            unlucky = min(table, key=lambda t: t["luck"])
            add("unlucky", "Unluckiest schedule", unlucky["h"],
                f"{unlucky['w']}-{unlucky['l']} with an all-play record of "
                f"{unlucky['allplay'][0]}-{unlucky['allplay'][1]}", unlucky["luck"])
            tp = max(table, key=lambda t: t["tops"])
            if tp["tops"]:
                add("tops", "Most weeks as top scorer", tp["h"],
                    f"{tp['tops']} week{'s' if tp['tops'] != 1 else ''} on top", tp["tops"])
            st = max(table, key=lambda t: t["streak"])
            if st["streak"] >= 3:
                add("streak", "Longest winning streak", st["h"],
                    f"{st['streak']} straight", st["streak"])

        if reg:
            hi = max(reg, key=lambda r: r["pts"])
            add("high", "Highest single week", hi["m"],
                f"{hi['pts']} in week {hi['w']} against {tn.get(hi['opp']) or hi['opp']}", hi["pts"])
            lo = min(reg, key=lambda r: r["pts"])
            add("low", "Lowest single week", lo["m"],
                f"{lo['pts']} in week {lo['w']} against {tn.get(lo['opp']) or lo['opp']}", lo["pts"])
            dec = [r for r in rs if r["pts"] != r["op"]]
            if dec:
                blow = max(dec, key=lambda r: r["pts"] - r["op"])
                add("blowout", "Biggest blowout", blow["m"],
                    f"beat {tn.get(blow['opp']) or blow['opp']} by "
                    f"{_r(blow['pts'] - blow['op'])} in week {blow['w']}",
                    _r(blow["pts"] - blow["op"]))
                close = min([r for r in dec if r["pts"] > r["op"]],
                            key=lambda r: r["pts"] - r["op"], default=None)
                if close:
                    add("closest", "Closest game", close["m"],
                        f"beat {tn.get(close['opp']) or close['opp']} by "
                        f"{_r(close['pts'] - close['op'])} in week {close['w']}",
                        _r(close["pts"] - close["op"]))
                losses = [r for r in dec if r["pts"] < r["op"]]
                if losses:
                    hard = max(losses, key=lambda r: r["pts"])
                    add("hard_luck", "Most points in a loss", hard["m"],
                        f"{hard['pts']} and still lost to "
                        f"{tn.get(hard['opp']) or hard['opp']} in week {hard['w']}", hard["pts"])
                wins = [r for r in dec if r["pts"] > r["op"]]
                if wins:
                    cheap = min(wins, key=lambda r: r["pts"])
                    add("cheap_win", "Fewest points in a win", cheap["m"],
                        f"won with {cheap['pts']} over "
                        f"{tn.get(cheap['opp']) or cheap['opp']} in week {cheap['w']}", cheap["pts"])

        # a title run from a low seed is the season's story more often than not
        if champ:
            cs = next((t for t in table if t["h"] == champ), None)
            if cs and cs["seed"] >= 4:
                add("cinderella", "Lowest seed to win it", champ,
                    f"won it from the {cs['seed']} seed at "
                    f"{cs['w']}-{cs['l']}", cs["seed"])

        out[str(season)] = dict(
            season=season,
            current=(season == cur),
            format=dict(teams=len(teams),
                        reg_weeks=max((r["w"] for r in reg), default=0),
                        playoff_weeks=sorted({r["w"] for r in po}),
                        scoring=scoring_era(season),
                        era=(rs[0]["era"] if rs else None),
                        games=len(rs) // 2),
            champion=champ, runner_up=runner, third=third, title_game=title,
            standings=table,
            bracket={k: v for k, v in bracket.items()},
            awards=aw,
        )
    return out


def build_seasons(ctx):
    data = ctx["data"]
    h = ctx.get("history")
    if not (isinstance(h, dict) and "games" in h and "fields" in h):
        h = ctx["read_json"](os.path.join(data, "history.json"), None)
    # src/lib/data, not static/data: the page imports it so the season renders
    # server-side, which a shared link preview and a search engine both need.
    doc = dict(generated=ctx.get("now"), seasons=build(h))
    ctx["write_json"](os.path.join(data, "seasons.json"), doc)
    return doc


if __name__ == "__main__":
    import io, json, sys
    repo = sys.argv[1]
    hp = os.path.join(repo, "src", "lib", "data", "history.json")
    h = json.load(io.open(hp, encoding="utf-8"))
    seasons = build(h)
    outp = os.path.join(repo, "src", "lib", "data", "seasons.json")
    with io.open(outp, "w", encoding="utf-8") as f:
        json.dump(dict(seasons=seasons), f, separators=(",", ":"))
    print(f"{os.path.basename(repo)}: {len(seasons)} seasons -> {outp}")
    print(f"  {os.path.getsize(outp)/1024:.0f}K")
    for y in sorted(seasons):
        s = seasons[y]
        print(f"  {y}: {s['format']['teams']} teams, {s['format']['reg_weeks']} reg weeks, "
              f"{len(s['awards'])} awards, champion {s['champion']}, "
              f"{len(s['bracket'])} bracket rounds, {s['format']['scoring']}")
