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


def mvp_awards(season, table, players, tn):
    """The two player awards T.J. picked (2026-11-16).

    MVP            most points scored while in a starting lineup that season.
    Most valuable  the biggest share of his own team's starting points, which
                   rewards a player who carried a weak roster over a star on a
                   stacked one. A team's PF IS its starting points, so the share
                   is the player's points over his owner's PF.

    A player traded or dropped mid-season has one stint per owner. MVP sums them
    (it is about the player's year); the share award uses the single stint, since
    a share only means something against one team.
    """
    if not players:
        return []
    pf = {t["h"]: t["pf"] for t in table}
    total, best_share = {}, None
    for p in players:
        name, pos = p.get("n"), p.get("p")
        for st in (p.get("s") or []):
            if len(st) < 4 or st[0] != season:
                continue
            owner, pts, starts = st[1], st[2] or 0, st[3] or 0
            if starts <= 0:
                continue
            key = (name, pos)
            cur = total.get(key) or [0.0, 0, set()]
            cur[0] += pts
            cur[1] += starts
            cur[2].add(owner)
            total[key] = cur
            own_pf = pf.get(owner) or 0
            if own_pf > 0 and starts >= 6:
                share = pts / own_pf
                if not best_share or share > best_share["share"]:
                    best_share = dict(name=name, pos=pos, owner=owner, pts=pts,
                                      starts=starts, share=share)

    out = []
    if total:
        (name, pos), (pts, starts, owners) = max(total.items(), key=lambda kv: kv[1][0])
        who = sorted(owners)[0]
        where = f"for {tn.get(who) or who}" if len(owners) == 1 else f"across {len(owners)} teams"
        out.append(dict(key="mvp", title="MVP", h=who, name=tn.get(who) or who,
                        player=name, pos=pos,
                        detail=f"{name} ({pos}) scored {_r(pts)} in {starts} starts {where}",
                        value=_r(pts)))
    if best_share:
        b = best_share
        out.append(dict(key="most_valuable", title="Most valuable to his team",
                        h=b["owner"], name=tn.get(b["owner"]) or b["owner"],
                        player=b["name"], pos=b["pos"],
                        detail=f"{b['name']} ({b['pos']}) was {round(b['share'] * 100, 1)}% of "
                               f"{tn.get(b['owner']) or b['owner']}'s starting points, "
                               f"{_r(b['pts'])} in {b['starts']} starts",
                        value=round(b["share"], 4)))
    return out


SLOT_ORDER = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "W/R/T": 4, "FLEX": 4, "K": 5, "DEF": 6}


def title_lineups(final, rows, tn):
    """Both starting lineups from the championship game, player by player.

    The title game is the one week everyone wants to re-litigate, and the data
    for it already exists - history.json labels the game, and the slot rows have
    week-level starters. Championship week is also when NFL teams with a locked
    playoff seed rest their starters, so a star scoring nothing in a final is
    often a real story rather than a bad week.
    """
    if not final or not rows:
        return None
    season, week = final["season"], final["week"]
    by_mgr = {}
    for r in rows:
        if len(r) < 8:
            continue
        s, w, h, _k, name, pos, started, pts = r[:8]
        if s != season or w != week or not started or h not in (final["a"], final["b"]):
            continue
        by_mgr.setdefault(h, []).append(dict(pos=pos or "", n=name, pts=round(pts or 0, 2)))
    if not by_mgr:
        return None
    for h in by_mgr:
        by_mgr[h].sort(key=lambda p: (SLOT_ORDER.get(p["pos"], 9), -p["pts"]))
    out = {}
    for h, lst in by_mgr.items():
        out[h] = dict(name=tn.get(h) or h, starters=lst,
                      total=round(sum(p["pts"] for p in lst), 2),
                      best=max(lst, key=lambda p: p["pts"]) if lst else None,
                      worst=min(lst, key=lambda p: p["pts"]) if lst else None)
    return out


def build(history, players=None, slot_rows=None):
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

        # the two player awards go first - they are about a player, not a manager
        aw = mvp_awards(season, table, players, tn) + aw

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
            title_lineups=title_lineups(
                dict(season=season, week=title["week"], a=title["a"], b=title["b"])
                if title else None, slot_rows, tn),
            standings=table,
            bracket={k: v for k, v in bracket.items()},
            awards=aw,
        )
    return out


def build_seasons(ctx, slot_rows=None):
    data = ctx["data"]
    h = ctx.get("history")
    if not (isinstance(h, dict) and "games" in h and "fields" in h):
        h = ctx["read_json"](os.path.join(data, "history.json"), None)
    # players.json carries per-stint points and starts, which the two player
    # awards need. It is optional: without it the season keeps its other awards.
    pl = None
    for base in (ctx.get("static_data"), data,
                 os.path.join(os.path.dirname(data), "..", "..", "static", "data")):
        if not base:
            continue
        p = os.path.join(base, "players.json")
        if os.path.exists(p):
            pl = (ctx["read_json"](p, None) or {}).get("players")
            break
    # src/lib/data, not static/data: the page imports it so the season renders
    # server-side, which a shared link preview and a search engine both need.
    doc = dict(generated=ctx.get("now"), seasons=build(h, pl, slot_rows))
    ctx["write_json"](os.path.join(data, "seasons.json"), doc)
    return doc


if __name__ == "__main__":
    import io, json, sys
    repo = sys.argv[1]
    hp = os.path.join(repo, "src", "lib", "data", "history.json")
    h = json.load(io.open(hp, encoding="utf-8"))
    pp = os.path.join(repo, "static", "data", "players.json")
    pl = (json.load(io.open(pp, encoding="utf-8")).get("players")
          if os.path.exists(pp) else None)
    # Standalone run: pull the vault's week-level slots so the title-game
    # lineups are built too. The real build passes rows in from extras instead.
    sr = None
    vault = os.environ.get("FLP_MANUAL") or \
        r"C:\Users\trick\Documents\Fantasy Football Vault\_manual"
    if os.path.isdir(vault):
        try:
            sys.path.insert(0, vault)
            import flp
            sr = [(x.season, x.week, x.manager, None, flp.norm_player(x.player),
                   x.pos or "", bool(x.started), round(x.points or 0, 2))
                  for x in flp.slots()]
            print(f"  vault slots: {len(sr)} player-weeks")
        except Exception as e:
            print("  no vault slots (%s) - title lineups will be empty" % e)
    seasons = build(h, pl, sr)
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
