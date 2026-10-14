"""trackers.py - season storylines and trackers, built at the Tuesday update.

Writes src/lib/data/trackers.json for the /trackers page. Every tracker is a
card: a title, a one-line note on how it is worked out, column names and rows.
A cell written "@@<handle>" is a team, and the page shows it with the team's
name and link. Each league gets the cards that fit its format; a card that
fails or has nothing to say is left out, never shown empty.

Sources, all read at build time:
  matchups (this season)       bench regret, coach of the year, hot hand,
                               records, kicker file, median misery, firsts
  Sleeper weekly projections   rest-of-season player values (ESPN's own for
                               League Bound), trade market, best bench
  ESPN NFL scoreboard          bye weeks
  Sleeper transactions         the one that got away, waiver king
  Sleeper traded_picks         dynasty draft capital
  Sleeper weekly stats         TE premium payoff
  odds.json, power.json, rosters.json, drafts, waivers   already built
"""
import os
import json
import statistics
import urllib.request
from collections import defaultdict

ELIG = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"}, "K": {"K"},
        "DEF": {"DEF"}, "FLEX": {"RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"},
        "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
CORE = ["QB", "RB", "WR", "TE"]
ESPN_SB = ("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
           "?week={week}&seasontype=2&dates={season}")
STATS_URL = "https://api.sleeper.app/stats/nfl/{season}/{week}?season_type=regular"
ESPN_TO_SLEEPER = {"WSH": "WAS"}


def T(h):
    return f"@@{h}"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "league-page-updater"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _best(slots, players, pts, pos_of):
    """Best legal lineup: (total, set of player ids used)."""
    order = sorted(slots, key=lambda s: len(ELIG.get(s, ())))
    used, total = set(), 0.0
    for s in order:
        best = None
        for p in players:
            if p in used or pos_of(p) not in ELIG.get(s, ()):
                continue
            if best is None or pts.get(p, 0) > pts.get(best, 0):
                best = p
        if best is not None:
            used.add(best)
            total += pts.get(best, 0)
    return total, used


def _r1(x):
    return round(x, 1)


def card(cid, title, note, cols, rows, **extra):
    if not rows:
        return None
    d = {"id": cid, "title": title, "note": note, "cols": cols, "rows": rows}
    d.update(extra)
    return d


class Ctx:
    """Everything the trackers share, loaded once."""

    def __init__(self, ctx):
        import insights as I
        self.ctx, self.I = ctx, I
        self.S = S = ctx["cur"]
        self.season = ctx["season"]
        self.read_json, self.write_json = ctx["read_json"], ctx["write_json"]
        self.data, self.static = ctx["data"], ctx["static"]
        self.repo = os.path.dirname(os.path.dirname(os.path.dirname(self.data)))
        self.dynasty = bool(ctx.get("dynasty"))
        self.slots = [s for s in (S.league.get("roster_positions") or []) if s in ELIG]
        self.scoring = S.league.get("scoring_settings") or {}
        self.score = I._scorer(self.scoring)
        self.pos_of = lambda pid: S.pinfo(pid)["pos"]
        self.done = [w for w in S.completed_weeks(ctx["state"]) if w < S.playoff_start]
        self.last = self.done[-1] if self.done else 0
        self.left = list(range(self.last + 1, S.playoff_start))
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "league_page_projections")
        sd = os.path.join(self.repo, "static", "shim", "v1", "projections")
        self.shim_dir = sd if os.path.isdir(sd) else None
        self.shim = bool(self.shim_dir)
        self.rosters = {S.handle.get(r["roster_id"]): [p for p in (r.get("players") or []) if p]
                        for r in S.rosters if S.handle.get(r["roster_id"])}
        self.teams = sorted(self.rosters)
        # this season's weekly lineups: week -> handle -> {players, starters, pts}
        self.weeks = {}
        for w in self.done:
            wk = {}
            for m in S.matchups(w):
                h = S.handle.get(m.get("roster_id"))
                if not h:
                    continue
                wk[h] = {"players": [p for p in (m.get("players") or []) if p],
                         "starters": [p for p in (m.get("starters") or []) if p and p != "0"],
                         "raw": list(m.get("starters") or []),
                         "pp": m.get("players_points") or {},
                         "pts": m.get("points") or 0, "mid": m.get("matchup_id")}
            self.weeks[w] = wk
        self.rinfo = {}
        for h, m in ((self.read_json(os.path.join(self.static, "rosters.json"), {}) or {})
                     .get("managers") or {}).items():
            for p in m.get("players") or []:
                self.rinfo[str(p.get("id"))] = p
        self.odds = self.read_json(os.path.join(self.data, "odds.json"), {}) or {}
        self.power = self.read_json(os.path.join(self.data, "power.json"), {}) or {}
        self._ros = None

    def txs(self):
        """This season's completed moves: (week, type, {pid: h} adds, {pid: h} drops, faab)."""
        if getattr(self, "_txs", None) is not None:
            return self._txs
        out = []
        for w in range(1, (self.last or 0) + 2):
            try:
                txs = self.ctx["sleeper"](f"/league/{self.S.league_id}/transactions/{w}") or []
            except Exception:
                continue
            for t in txs:
                if t.get("status") != "complete":
                    continue
                adds = {str(p): self.S.handle.get(r) for p, r in (t.get("adds") or {}).items() if self.S.handle.get(r)}
                drops = {str(p): self.S.handle.get(r) for p, r in (t.get("drops") or {}).items() if self.S.handle.get(r)}
                faab = (t.get("settings") or {}).get("waiver_bid")
                out.append((w, t.get("type") or "", adds, drops, faab))
        self._txs = out
        return out

    def started_since(self, h, pid, week):
        """Points and starts for pid in h's starting lineup from week on."""
        pts, n = 0.0, 0
        for w, wk in self.weeks.items():
            if w < week or h not in wk:
                continue
            if pid in wk[h]["starters"]:
                pts += float(wk[h]["pp"].get(pid, 0) or 0)
                n += 1
        return pts, n

    def week_stats(self, w):
        """pid -> that week's raw stat line (Sleeper), cached on disk."""
        path = os.path.join(self.cache_dir, f"fullstats-{self.season}-w{w:02d}.json")
        st = self.read_json(path, None)
        if st is None:
            try:
                raw = _get(STATS_URL.format(season=self.season, week=w)) or []
            except Exception as e:
                print("trackers: weekly stats unavailable", w, e)
                return {}
            if isinstance(raw, dict):
                st = {k: v or {} for k, v in raw.items()}
            else:
                st = {r["player_id"]: (r.get("stats") or {}) for r in raw if r.get("player_id")}
            if w < self.last or w == self.last:
                self.write_json(path, st, compact=True)
        return st

    def name(self, pid):
        i = self.S.pinfo(pid)
        return i["name"], i["pos"], i.get("team") or ""

    def games(self):
        """This season's regular-season games: (week, a, pa, b, pb)."""
        out = []
        for g in self.ctx["history"]["games"]:
            s, w, _e, a, pa, b, pb, playoff, _l = g
            if s == self.season and not playoff and w in self.weeks:
                out.append((w, a, pa, b, pb))
        return out

    def ros(self):
        """pid -> average projected points per remaining week, and per week."""
        if self._ros is not None:
            return self._ros
        per_week, tot, n = {}, defaultdict(float), 0
        for w in self.left:
            try:
                proj = self.I._projections(self.season, w, self.cache_dir, self.read_json,
                                           self.write_json, final=False, shim_dir=self.shim_dir)
            except Exception as e:
                print("trackers: projections unavailable for week", w, e)
                continue
            if not proj:
                continue
            n += 1
            wk = {}
            for h, players in self.rosters.items():
                for p in players:
                    v = self.score(proj.get(p)) or 0
                    wk[p] = v
                    tot[p] += v
            per_week[w] = wk
        avg = {p: tot[p] / n for p in tot} if n else {}
        self._ros = (avg, per_week, n)
        return self._ros


# ------------------------------------------------------------ the wire
def wire_data(C):
    """Unrostered players each week, scored with this league's scoring, and the best
    single swap each team could have made. Cached on C."""
    if getattr(C, "_wire", None) is not None:
        return C._wire
    out = {"flips": [], "missed": defaultdict(float), "flipcount": defaultdict(int),
           "ok": False, "checked": 0, "agree": 0}
    C._wire = out
    positions = [x for x in (C.S.league.get("roster_positions") or []) if x not in ("BN", "IR", "TAXI")]
    if not C.scoring or not positions:
        return out
    for w, wk in sorted(C.weeks.items()):
        st = C.week_stats(w)
        if not st:
            continue
        rostered = {x for t in wk.values() for x in t["players"]}
        for t in wk.values():
            for x in t["starters"]:
                if x in t["pp"] and x in st:
                    out["checked"] += 1
                    out["agree"] += abs((C.score(st[x]) or 0) - float(t["pp"][x] or 0)) <= 0.11
        fa = {}
        for pid, line in st.items():
            # TEAM_XX lines are whole-team totals, not a rosterable defense
            if pid in rostered or not line or pid.startswith("TEAM_") or C.pos_of(pid) not in ("QB", "RB", "WR", "TE", "K", "DEF"):
                continue
            v = C.score(line)
            if v and v > 0:
                fa[pid] = v
        top = {}

        def best_for(slot):
            if slot not in top:
                el = ELIG.get(slot, ())
                cands = [(v, x) for x, v in fa.items() if C.pos_of(x) in el]
                top[slot] = max(cands) if cands else None
            return top[slot]

        pairs = defaultdict(list)
        for h, t in wk.items():
            if t["mid"] is not None:
                pairs[t["mid"]].append(h)
        for h, t in wk.items():
            best = None
            for i, slot in enumerate(positions):
                if slot not in ELIG or i >= len(t["raw"]):
                    continue
                cur = t["raw"][i]
                cur_pts = float(t["pp"].get(cur, 0) or 0) if cur and cur != "0" else 0.0
                b = best_for(slot)
                if b and (best is None or b[0] - cur_pts > best[0]):
                    best = (b[0] - cur_pts, b[1], b[0], cur, cur_pts)
            if not best or best[0] <= 0:
                continue
            out["missed"][h] += best[0]
            opp = [x for x in pairs.get(t["mid"], []) if x != h]
            if not opp:
                continue
            margin = wk[opp[0]]["pts"] - t["pts"]
            if margin > 0 and best[0] > margin:
                out["flipcount"][h] += 1
                gone = C.name(best[3])[0] if best[3] and best[3] != "0" else "an empty slot"
                nm, pos, _tm = C.name(best[1])
                out["flips"].append([w, T(h), T(opp[0]), f"{nm} ({pos}) {_r1(best[2])}",
                                     f"{gone} {_r1(best[4])}", _r1(margin)])
    out["ok"] = out["checked"] > 0 and out["agree"] / out["checked"] >= 0.9
    print(f"trackers: wire {'on' if out['ok'] else 'skipped'}, scoring matched "
          f"{out['agree']} of {out['checked']} started players")
    return out


def wire_flips(C):
    W = wire_data(C)
    if not W["ok"]:
        return []
    rows = sorted(W["flips"], key=lambda r: (-r[0], -r[5]))
    return [card("wire_flips", "The wire would have won it",
                 "Losses that one unrostered player would have turned into a win: the best free agent that week, "
                 "scored with this league's settings, in for a starter at a slot he could fill. "
                 "Unrostered means not on any roster by the end of that week; waiver timing and game locks are not checked.",
                 ["Week", "Team", "Lost to", "Free agent", "In for", "Lost by"], rows)]


# ------------------------------------------------------------ trade market
def trade_market(C):
    avg, _pw, n = C.ros()
    if not n:
        return []
    need_n = {p: sum(1 for s in C.slots if s == p) for p in CORE}
    for s in C.slots:                      # flex spots count half toward each position they take
        el = ELIG[s] & set(CORE)
        if len(el) > 1:
            for p in el:
                need_n[p] += 1 / len(el)
    strength, depth = {}, {}
    for h, players in C.rosters.items():
        for p in CORE:
            vals = sorted((avg.get(x, 0) for x in players if C.pos_of(x) == p), reverse=True)
            k = max(1, round(need_n[p]))
            strength[(h, p)] = sum(vals[:k])
            depth[(h, p)] = vals[k:]
    rank = {}
    for p in CORE:
        order = sorted(C.teams, key=lambda h: -strength[(h, p)])
        for i, h in enumerate(order):
            rank[(h, p)] = i + 1
    third = max(1, len(C.teams) // 3)
    # a surplus: a bench player at that spot who would start for the median team
    med_last = {}
    for p in CORE:
        k = max(1, round(need_n[p]))
        lasts = []
        for h, players in C.rosters.items():
            vals = sorted((avg.get(x, 0) for x in players if C.pos_of(x) == p), reverse=True)
            lasts.append(vals[k - 1] if len(vals) >= k else 0)
        med_last[p] = statistics.median(lasts) if lasts else 0
    needs = {h: [p for p in CORE if rank[(h, p)] > len(C.teams) - third] for h in C.teams}
    surplus = {h: [p for p in CORE if p not in needs[h] and depth[(h, p)]
                   and depth[(h, p)][0] >= 0.85 * med_last[p]] for h in C.teams}
    rows = []
    for h in sorted(C.teams, key=lambda h: (len(needs[h]) == 0, h)):
        rows.append([T(h), ", ".join(surplus[h]) or "-", ", ".join(needs[h]) or "-",
                     " ".join(f"{p} {rank[(h, p)]}" for p in CORE)])
    cards = [card("market", "Trade market",
                  f"Need: a starting group in the bottom third of the league on rest-of-season projections. "
                  f"Surplus: a bench player close to what the middle team starts at that spot. Over {n} weeks of projections.",
                  ["Team", "Surplus", "Need", "Starter rank by position"], rows)]
    pairs = []
    for i, a in enumerate(C.teams):
        for b in C.teams[i + 1:]:
            ab = [p for p in surplus[a] if p in needs[b]]
            ba = [p for p in surplus[b] if p in needs[a]]
            both = set(ab) & set(ba)               # a QB for a QB is not a trade
            ab, ba = [p for p in ab if p not in both], [p for p in ba if p not in both]
            if ab and ba:
                pairs.append([T(a), "/".join(ab), T(b), "/".join(ba)])
    cards.append(card("partners", "Natural trade partners",
                      "Pairs where each side has a surplus at the other's weak spot.",
                      ["Team", "Can send", "Partner", "Can send back"], pairs[:12]))
    sell = []
    for h, players in C.rosters.items():
        for p in CORE:
            k = max(1, round(need_n[p]))
            ranked = sorted((x for x in players if C.pos_of(x) == p), key=lambda x: -avg.get(x, 0))
            for x in ranked[k:]:
                if avg.get(x, 0) >= 0.85 * med_last[p] and p in surplus[h]:
                    nm, pos, tm = C.name(x)
                    sell.append([T(h), nm, f"{pos} {tm}".strip(), _r1(avg.get(x, 0))])
    sell.sort(key=lambda r: -r[3])
    cards.append(card("sell", "Selling pieces",
                      "Bench players projected close to a starter for most teams. Points are projected per remaining week.",
                      ["Team", "Player", "Pos", "Proj/wk"], sell[:15]))
    return cards


# ------------------------------------------------------------ bench and byes
def bench(C):
    cards = []
    avg, per_week, n = C.ros()
    if n:
        rows = []
        for h, players in C.rosters.items():
            _t, used = _best(C.slots, players, avg, C.pos_of)
            rest = sorted((x for x in players if x not in used and C.pos_of(x) in CORE), key=lambda x: -avg.get(x, 0))
            top = rest[:3]
            rows.append([T(h), _r1(sum(avg.get(x, 0) for x in top)),
                         ", ".join(C.name(x)[0] for x in top)])
        rows.sort(key=lambda r: -r[1])
        for i, r in enumerate(rows):
            r.insert(0, i + 1)
        cards.append(card("bench", "Best bench",
                          "The three best bench players on rest-of-season projections, per week combined. Depth for byes and injuries.",
                          ["#", "Team", "Top 3 bench / wk", "Who"], rows))
    # season bench regret: best possible lineup on actual points vs what was started
    reg, eff, cnt = defaultdict(float), defaultdict(list), defaultdict(int)
    worst = []
    for w, wk in C.weeks.items():
        for h, t in wk.items():
            pts = {p: float(t["pp"].get(p, 0) or 0) for p in t["players"]}
            opt, _u = _best(C.slots, t["players"], pts, C.pos_of)
            got = sum(pts.get(p, 0) for p in t["starters"])
            if opt <= 0:
                continue
            reg[h] += opt - got
            eff[h].append(got / opt)
            worst.append([w, T(h), _r1(opt - got)])
    if reg:
        rows = sorted(([T(h), _r1(reg[h]), f"{round(100 * statistics.mean(eff[h]))}%"] for h in reg),
                      key=lambda r: -r[1])
        cards.append(card("regret", "Bench regret",
                          "Points left on the bench all season: the best lineup each week on real points, minus the lineup that was started.",
                          ["Team", "Points left", "Lineup efficiency"], rows))
        worst.sort(key=lambda r: -r[2])
        cards.append(card("regret_week", "Worst lineup weeks",
                          "The single weeks with the most points sitting on the bench.",
                          ["Week", "Team", "Points left"], worst[:6]))
        W = wire_data(C)
        coach = sorted(([T(h), f"{round(100 * statistics.mean(eff[h]), 1)}%", len(eff[h])]
                        + ([W["flipcount"].get(h, 0)] if W["ok"] else []) for h in eff),
                       key=lambda r: -float(r[1][:-1]))
        cards.append(card("coach", "Coach of the year",
                          "Average lineup efficiency: started points as a share of the best possible lineup each week."
                          + (" Wire flips: losses one free agent would have turned into wins." if W["ok"] else ""),
                          ["Team", "Efficiency", "Weeks"] + (["Wire flips"] if W["ok"] else []), coach, race=True))
    cards += byes(C)
    return cards


def byes(C):
    if not C.left:
        return []
    cache = os.path.join(C.data, "nfl_byes.json")
    have = C.read_json(cache, None) or {}
    if have.get("season") != C.season:
        played, allteams = {}, set()
        try:
            for w in range(1, 19):
                sb = _get(ESPN_SB.format(week=w, season=C.season))
                ts = set()
                for ev in sb.get("events") or []:
                    for comp in ev.get("competitions") or []:
                        for c in comp.get("competitors") or []:
                            a = (c.get("team") or {}).get("abbreviation")
                            if a:
                                ts.add(ESPN_TO_SLEEPER.get(a, a))
                played[w] = ts
                allteams |= ts
        except Exception as e:
            print("trackers: bye weeks unavailable", e)
            return []
        have = {"season": C.season, "byes": {str(w): sorted(allteams - ts) for w, ts in played.items() if ts}}
        C.write_json(cache, have)
    bye = {int(w): set(v) for w, v in (have.get("byes") or {}).items()}
    avg, per_week, n = C.ros()
    if not n:
        return []
    rows = []
    for w in C.left[:4]:
        off = bye.get(w) or set()
        if not off:
            continue
        for h, players in C.rosters.items():
            _t, used = _best(C.slots, players, avg, C.pos_of)
            hit = [x for x in used if (C.S.pinfo(x).get("team") or "") in off]
            if len(hit) >= 2:
                lost = sum(avg.get(x, 0) for x in hit)
                rows.append([w, T(h), len(hit), _r1(lost), ", ".join(C.name(x)[0] for x in hit)])
    rows.sort(key=lambda r: (r[0], -r[3]))
    out = [card("byes", "Bye week danger",
                "Teams losing two or more of their usual starters to byes in the next four weeks, with those starters' projected points.",
                ["Week", "Team", "Starters out", "Proj pts lost", "Who"], rows[:12])]
    return out


# ------------------------------------------------------------ season races
def races(C, waivers, drafts):
    cards = []
    g = C.games()
    # hot hand: last three weeks against the season
    sc = defaultdict(dict)
    for w, a, pa, b, pb in g:
        sc[a][w] = pa
        sc[b][w] = pb
    if len(C.done) >= 4:
        rows = []
        for h, d in sc.items():
            ws = sorted(d)
            if len(ws) < 4:
                continue
            l3 = statistics.mean(d[w] for w in ws[-3:])
            se = statistics.mean(d.values())
            rows.append([T(h), _r1(l3), _r1(se), _r1(l3 - se)])
        rows.sort(key=lambda r: -r[3])
        cards.append(card("hot", "Hot hand",
                          "Points per game over the last three weeks against the season average.",
                          ["Team", "Last 3", "Season", "Change"], rows))
    # pickup of the year and waiver king
    cur, seen = [], set()
    for w, typ, adds, _d, faab in C.txs():
        if typ not in ("waiver", "free_agent"):
            continue
        for pid, h in adds.items():
            if (h, pid) in seen:
                continue
            seen.add((h, pid))
            pts, st = C.started_since(h, pid, w)
            cur.append({"h": h, "n": C.name(pid)[0], "pts": pts, "st": st, "faab": faab or 0})
    if cur:
        top = sorted((p for p in cur if p.get("pts")), key=lambda p: -p["pts"])[:8]
        cards.append(card("pickup", "Pickup of the year",
                          "Waiver and free-agent adds this season, by points scored in that team's starting lineup since.",
                          ["Team", "Player", "Started pts", "Starts", "FAAB"],
                          [[T(p["h"]), p["n"], _r1(p.get("pts") or 0), p.get("st", 0),
                            (f"${p['faab']}" if p.get("faab") else "-")] for p in top], race=True))
        by = defaultdict(lambda: [0, 0.0, 0])
        for p in cur:
            b = by[p["h"]]
            b[0] += 1
            b[1] += p.get("pts") or 0
            b[2] += p.get("faab") or 0
        rows = sorted(([T(h), v[0], _r1(v[1]), (f"${v[2]}" if v[2] else "-")] for h, v in by.items()),
                      key=lambda r: -r[2])
        cards.append(card("wire", "Waiver king",
                          "Started points from this season's pickups, team by team.",
                          ["Team", "Adds", "Started pts", "FAAB spent"], rows, race=True))
    cards += got_away(C)
    cards += gm(C)
    # locks and long shots
    ot = C.odds.get("teams") or []
    if ot and C.odds.get("season") == C.season:
        hist = C.odds.get("history") or {}
        first_wk = min((int(k) for k in hist), default=0)
        first = (hist.get(str(first_wk)) or {}) if len(hist) > 1 else {}
        if first and all(abs(t["playoff"] - first.get(t["h"], t["playoff"])) < 0.05 for t in ot):
            first = {}                     # odds only started being kept this week
        rows = []
        for t in sorted(ot, key=lambda t: -t["playoff"]):
            tag = ("Lock" if t["playoff"] >= 90 else "Long shot" if t["playoff"] <= 10 else
                   "Likely" if t["playoff"] >= 65 else "Bubble" if t["playoff"] >= 35 else "Fading")
            move = t["playoff"] - first.get(t["h"], t["playoff"])
            row = [T(t["h"]), f"{t['playoff']}%", tag]
            if first:
                row.append(f"+{_r1(move)}" if move > 0 else _r1(move))
            rows.append(row)
        cols = ["Team", "Playoffs", "Status"] + ([f"Since week {first_wk}"] if first else [])
        cards.append(card("locks", "Locks and long shots",
                          f"Playoff chances from {C.odds.get('sims', 10000):,} simulated seasons"
                          + (f", and the move since week {first_wk}." if first else "."), cols, rows))
    # records so far
    if g:
        hi = max(g, key=lambda x: max(x[2], x[4]))
        lo = min(g, key=lambda x: min(x[2], x[4]))
        blow = max(g, key=lambda x: abs(x[2] - x[4]))
        close = min((x for x in g if x[2] != x[4]), key=lambda x: abs(x[2] - x[4]), default=None)
        both = max(g, key=lambda x: x[2] + x[4])
        rows = []
        w, a, pa, b, pb = hi
        rows.append(["Highest score", T(a if pa >= pb else b), _r1(max(pa, pb)), f"Week {w}"])
        w, a, pa, b, pb = lo
        rows.append(["Lowest score", T(a if pa <= pb else b), _r1(min(pa, pb)), f"Week {w}"])
        w, a, pa, b, pb = blow
        rows.append(["Biggest blowout", T(a if pa > pb else b), f"by {_r1(abs(pa - pb))}", f"Week {w}"])
        if close:
            w, a, pa, b, pb = close
            rows.append(["Closest game", T(a if pa > pb else b), f"by {round(abs(pa - pb), 2)}", f"Week {w}"])
        w, a, pa, b, pb = both
        rows.append(["Best shootout", T(a), f"{_r1(pa)} to {_r1(pb)}", f"Week {w}"])
        cards.append(card("records", "Season records so far", "Regular season, this year.",
                          ["Record", "Team", "Mark", "When"], rows))
    return cards


def got_away(C):
    """Players a team cut this season who scored most for someone else after."""
    last_drop = {}
    for w, typ, _a, drops, _f in C.txs():
        if typ == "trade":                 # a trade is not a cut
            continue
        for pid, h in drops.items():
            last_drop[(h, pid)] = w
    rows = []
    for (h, pid), w in last_drop.items():
        after, holder = 0.0, None
        for wk in sorted(C.weeks):
            if wk < w:
                continue
            for h2, t in C.weeks[wk].items():
                if pid in t["starters"] and h2 != h:
                    after += float(t["pp"].get(pid, 0) or 0)
                    holder = h2
        if after > 0 and holder:
            nm, pos, _tm = C.name(pid)
            rows.append([T(h), nm, pos, w, T(holder), _r1(after)])
    rows.sort(key=lambda r: -r[5])
    return [card("gotaway", "The one that got away",
                 "Players cut this season, by points they have since scored in someone else's starting lineup.",
                 ["Cut by", "Player", "Pos", "Week", "Now starting for", "Pts since"], rows[:8])]


def gm(C):
    """Points started this season by players a team brought in by trade or the wire."""
    tot, n, seen = defaultdict(float), defaultdict(set), set()
    for w, typ, adds, _d, _f in C.txs():
        if typ not in ("trade", "waiver", "free_agent"):
            continue
        for pid, h in adds.items():
            if (h, pid) in seen:
                continue
            seen.add((h, pid))
            pts, st = C.started_since(h, pid, w)
            if st:
                tot[h] += pts
                n[h].add(pid)
    if not tot:
        return []
    W = wire_data(C)
    rows = sorted(([T(h), _r1(v), len(n[h])] + ([_r1(W["missed"].get(h, 0))] if W["ok"] else [])
                   for h, v in tot.items()), key=lambda r: -r[1])
    return [card("gm", "GM of the year",
                 "Points started this season by players brought in by trade or off the wire, not the draft."
                 + (" Wire pts missed: each week's best possible free-agent upgrade over a starter, added up."
                    if W["ok"] else ""),
                 ["Team", "Started pts", "Players used"] + (["Wire pts missed"] if W["ok"] else []), rows, race=True)]


# ------------------------------------------------------------ dynasty
def dynasty(C):
    if not C.dynasty:
        return []
    cards = []
    pw = {t["h"]: t for t in (C.power.get("teams") or [])}
    ages = {}
    for h, players in C.rosters.items():
        a = [C.rinfo[str(p)].get("age") for p in players if str(p) in C.rinfo and C.rinfo[str(p)].get("age")
             and C.pos_of(p) in CORE]
        ages[h] = statistics.mean(a) if a else None
    if pw and all(pw.get(h, {}).get("dyn_rank") for h in C.teams):
        half = len(C.teams) / 2
        rows = []
        for h in C.teams:
            t = pw[h]
            now = t.get("ros_rank") or t["rank"]
            fut = t["dyn_rank"]
            lab = ("Dynasty power" if now <= half and fut <= half else
                   "Win now" if now <= half else
                   "Built for later" if fut <= half else "Rebuild")
            rows.append([T(h), now, fut, (_r1(ages[h]) if ages[h] else "-"), lab])
        rows.sort(key=lambda r: r[1] + r[2])
        cards.append(card("quadrant", "Contender or rebuilder",
                          "This year: rest-of-season projection rank. Future: FantasyPros dynasty roster value rank. Age: average age of rostered QB, RB, WR and TE.",
                          ["Team", "This year", "Future", "Avg age", "Window"], rows))
    # draft capital
    try:
        tp = C.ctx["sleeper"](f"/league/{C.S.league_id}/traded_picks") or []
    except Exception:
        tp = []
    rounds = int((C.S.league.get("settings") or {}).get("draft_rounds") or 4)
    years = [C.season + i for i in (1, 2, 3)]
    rid_h = dict(C.S.handle)
    own = {(y, r, rid): rid for y in years for r in range(1, rounds + 1) for rid in rid_h}
    for t in tp:
        try:
            y = int(t["season"])
        except Exception:
            continue
        if y in years:
            own[(y, int(t["round"]), t["roster_id"])] = t["owner_id"]
    cap = defaultdict(lambda: defaultdict(int))
    for (y, r, orig), owner in own.items():
        if owner in rid_h:
            cap[rid_h[owner]][(y, r)] += 1
    rows = []
    for h in C.teams:
        firsts = sum(cap[h][(y, 1)] for y in years)
        tot = sum(cap[h].values())
        pts = sum(v * (rounds + 1 - r) for (y, r), v in cap[h].items())
        rows.append([T(h), firsts, sum(cap[h][(y, 2)] for y in years), tot, pts,
                     " ".join(f"{str(y)[2:]}:{sum(cap[h][(y, r)] for r in range(1, rounds + 1))}" for y in years)])
    rows.sort(key=lambda r: -r[4])
    for r in rows:
        r.pop(4)
    cards.append(card("capital", "Draft capital",
                      f"Picks owned for {years[0]} to {years[-1]}, from Sleeper's traded-pick ledger. Sorted with earlier rounds worth more.",
                      ["Team", "1sts", "2nds", "Total", "By year"], rows))
    # QB room
    avg, _pw2, n = C.ros()
    if n and any(s == "SUPER_FLEX" for s in C.slots):
        allq = sorted((p for ps in C.rosters.values() for p in ps if C.pos_of(p) == "QB"),
                      key=lambda p: -avg.get(p, 0))
        startable = set(allq[:24])
        rows = []
        for h, players in C.rosters.items():
            q = sorted((p for p in players if C.pos_of(p) == "QB"), key=lambda p: -avg.get(p, 0))
            rows.append([T(h), len(q), sum(1 for p in q if p in startable),
                         ", ".join(f"{C.name(p)[0]} {_r1(avg.get(p, 0))}" for p in q[:3])])
        rows.sort(key=lambda r: (-r[2], -r[1]))
        cards.append(card("qbroom", "Superflex QB room",
                          "Starting QBs (top 24 on rest-of-season projections) per team. Two is the goal; three is trade capital.",
                          ["Team", "QBs", "Starters", "Top QBs (proj/wk)"], rows))
    # RB age watch
    rows = []
    for h, players in C.rosters.items():
        rk = pw.get(h, {}).get("rank", 99)
        for p in players:
            i = C.rinfo.get(str(p)) or {}
            if C.pos_of(p) == "RB" and (i.get("age") or 0) >= 27:
                rows.append([T(h), C.name(p)[0], i["age"], rk, _r1(avg.get(p, 0)) if n else "-"])
    rows.sort(key=lambda r: (r[3], -r[2]))
    cards.append(card("rbage", "RB age watch",
                      "Running backs 27 and older, by their team's power rank. Contenders ride them; everyone else should be shopping them.",
                      ["Team", "Player", "Age", "Team power", "Proj/wk"], rows[:15]))
    # rookies
    rows = []
    season_pts = defaultdict(float)
    for wk in C.weeks.values():
        for t in wk.values():
            for p, v in t["pp"].items():
                season_pts[p] += float(v or 0)
    for h, players in C.rosters.items():
        for p in players:
            i = C.rinfo.get(str(p)) or {}
            if i.get("exp") == 0 and C.pos_of(p) in CORE:
                rows.append([C.name(p)[0], C.pos_of(p), T(h), _r1(season_pts.get(p, 0))])
    rows.sort(key=lambda r: -r[3])
    cards.append(card("rookies", "Rookie tracker",
                      "Every rostered rookie, by points this season.",
                      ["Player", "Pos", "Team", "Pts"], rows[:20]))
    cards += te_premium(C)
    return cards


def te_premium(C):
    bonus = float(C.scoring.get("bonus_rec_te") or 0)
    if not bonus:
        return []
    got = defaultdict(float)
    who = defaultdict(lambda: defaultdict(float))
    for w, wk in C.weeks.items():
        path = os.path.join(C.cache_dir, f"stats-{C.season}-w{w:02d}.json")
        st = C.read_json(path, None)
        if st is None:
            try:
                raw = _get(STATS_URL.format(season=C.season, week=w)) or []
            except Exception as e:
                print("trackers: stats unavailable", w, e)
                return []
            if isinstance(raw, dict):
                st = {k: (v or {}).get("rec", 0) for k, v in raw.items()}
            else:
                st = {r["player_id"]: (r.get("stats") or {}).get("rec", 0) for r in raw if r.get("player_id")}
            C.write_json(path, st, compact=True)
        for h, t in wk.items():
            for p in t["starters"]:
                if C.pos_of(p) == "TE":
                    b = (st.get(p) or 0) * bonus
                    got[h] += b
                    who[h][p] += b
    if not got:
        return []
    rows = []
    for h in sorted(got, key=lambda h: -got[h]):
        top = max(who[h], key=lambda p: who[h][p]) if who[h] else None
        rows.append([T(h), _r1(got[h]), C.name(top)[0] if top else "-"])
    return [card("tep", "TE premium payoff",
                 f"Extra points this season from the +{bonus:g} per TE catch, started tight ends only.",
                 ["Team", "Premium pts", "Top earner"], rows)]


# ------------------------------------------------------------ league specials
def kicker_file(C):
    """Games this season that the kickers decided."""
    rows = []
    for w, a, pa, b, pb in C.games():
        wk = C.weeks.get(w) or {}
        if a not in wk or b not in wk or pa == pb:
            continue
        k = {h: sum(float(wk[h]["pp"].get(p, 0) or 0) for p in wk[h]["starters"] if C.pos_of(p) == "K")
             for h in (a, b)}
        win, lose = (a, b) if pa > pb else (b, a)
        margin = abs(pa - pb)
        if k[win] - k[lose] > margin:
            rows.append([w, T(win), T(lose), round(margin, 2), f"{_r1(k[win])} to {_r1(k[lose])}"])
    return [card("kickers", "The kicker file",
                 "Games this season where the kickers decided it: take both kickers out and the result flips.",
                 ["Week", "Winner", "Loser", "Margin", "Kickers"], rows)] if rows else \
        [card("kickers", "The kicker file", "Games the kickers decided this season.",
              ["Status"], [["No game has been decided by the kickers yet."]])]


def board_duty(C):
    ot = C.odds.get("teams") or []
    if not ot or "board" not in ot[0]:
        return []
    # Board duty goes to the loser of the losers bracket (T.J., 2026-10-14), not
    # regular-season last place. The odds sim plays out Sleeper's losers bracket.
    rows = sorted(([T(t["h"]), f"{t['board']}%", f"{t['last']}%", f"{t['playoff']}%", f"{t['w']}-{t['l']}"]
                   for t in ot if t.get("board", 0) > 0),
                  key=lambda r: -float(r[1][:-1]))
    return [card("board", "Board duty race",
                 "Chance of losing the losers bracket, played out in the same simulations as the playoff "
                 "odds. In Sleeper's losers bracket the worst two teams get byes and the loser of each game "
                 "moves on, so finishing last does not settle it.",
                 ["Team", "Board duty", "Last place", "Playoffs", "Record"], rows)]


def draft_report(C):
    traded = {(h, C.name(pid)[0]) for w, typ, _a, drops, _f in C.txs() if typ == "trade" for pid, h in drops.items()}
    picks = [p for p in (C.drafts.get("picks") or []) if p[0] == C.season and p[2]
             and p[5] in CORE and (p[3], p[4]) not in traded]
    if len(picks) < 20:
        return []
    by_val = sorted(picks, key=lambda p: -(p[6] or 0))
    vrank = {id(p): i + 1 for i, p in enumerate(by_val)}
    steals = sorted(picks, key=lambda p: -(p[2] - vrank[id(p)]))[:6]
    busts = sorted((p for p in picks if p[2] <= len(C.teams) * 5), key=lambda p: -(vrank[id(p)] - p[2]))[:6]
    cols = ["Pick", "Team", "Player", "Pos", "Value rank"]
    fmt = lambda p: [f"{p[1]}.{((p[2] - 1) % len(C.teams)) + 1:02d}", T(p[3]), p[4], p[5], vrank[id(p)]]
    return [card("steals", "Draft steals", "This year's QB, RB, WR and TE picks returning far more than their draft slot, by started points for the team that drafted them. Traded players left out.",
                 cols, [fmt(p) for p in steals]),
            card("busts", "Draft busts", "Early picks (first five rounds) returning the least so far. Traded players left out.",
                 cols, [fmt(p) for p in busts])]


def names_log(C):
    """Every name each team has gone by: the season-end name for every season on record
    (history.json team_names), plus renames caught by the daily build (team_names.json)."""
    path = os.path.join(C.data, "team_names.json")
    log = C.read_json(path, {}) or {}
    hist = log.get("history") or {}
    try:
        users = C.ctx["sleeper"](f"/league/{C.S.league_id}/users") or []
        by_user = {u.get("user_id"): ((u.get("metadata") or {}).get("team_name") or "") for u in users}
        for r in C.S.rosters:
            h = C.S.handle.get(r["roster_id"])
            nm = by_user.get(r.get("owner_id"), "").strip()
            if h and nm:
                seen = hist.setdefault(h, [])
                if not seen or seen[-1]["name"] != nm:
                    seen.append({"name": nm, "since": f"{C.season} week {C.last}"})
    except Exception as e:
        print("trackers: team names unavailable", e)
    C.write_json(path, {"history": hist})
    by_season = (C.ctx["history"].get("team_names") or {})
    current = set(C.teams)
    rows = []
    for h in sorted(current):
        names = []   # (label, name), oldest first, consecutive repeats dropped

        def add(label, nm):
            nm = (nm or "").strip()
            if nm and nm != h and (not names or names[-1][1] != nm):
                names.append((label, nm))
        for season in sorted(by_season, key=int):
            add(season, (by_season.get(season) or {}).get(h))
        for e in hist.get(h, []):
            add(e["since"].split(" week ")[0] + " (wk " + e["since"].split(" week ")[-1] + ")", e["name"])
        if not names:
            continue
        is_now = names[-1][0].startswith(str(C.season))
        now = names[-1][1] if is_now else "no team name set"
        older = names[:-1] if is_now else names
        before = " / ".join(f"{nm} ({lab})" for lab, nm in reversed(older[-5:])) or "-"
        rows.append([T(h), len({nm for _l, nm in names}), now, before])
    rows.sort(key=lambda r: -r[1])
    return [card("names", "Team name history",
                 "Every name a team has gone by: its name at the end of each season on record, "
                 "plus renames caught by the daily update from October 2026 on. Before shows the last five, newest first.",
                 ["Team", "Names", "Now", "Before"], rows)]


def median_misery(C):
    if not C.odds.get("median"):
        return []
    lost_h2h_beat_med, won_h2h_lost_med = defaultdict(int), defaultdict(int)
    for w, wk in C.weeks.items():
        scores = [t["pts"] for t in wk.values()]
        if not scores:
            continue
        med = statistics.median(scores)
        for x, a, pa, b, pb in C.games():
            if x != w:
                continue
            for h, me, opp in ((a, pa, pb), (b, pb, pa)):
                if me < opp and me > med:
                    lost_h2h_beat_med[h] += 1
                if me > opp and me < med:
                    won_h2h_lost_med[h] += 1
    rows = [[T(h), lost_h2h_beat_med[h], won_h2h_lost_med[h], lost_h2h_beat_med[h] - won_h2h_lost_med[h]]
            for h in C.teams]
    rows.sort(key=lambda r: -r[3])
    return [card("median", "Median misery",
                  "Split weeks: beat the median but lost the game (unlucky), or won the game but lost to the median (bailed out).",
                  ["Team", "Unlucky splits", "Bailed out", "Net"], rows)]


def qb_race(C):
    tot, team = defaultdict(float), {}
    for w, wk in C.weeks.items():
        for h, t in wk.items():
            for p in t["players"]:
                if C.pos_of(p) == "QB":
                    tot[p] += float(t["pp"].get(p, 0) or 0)
                    team[p] = h
    rows = sorted(([C.name(p)[0], C.name(p)[2], T(team[p]), _r1(v)] for p, v in tot.items()), key=lambda r: -r[3])
    ptd = C.scoring.get("pass_td")
    return [card("qbrace", "QB race",
                 f"Rostered quarterbacks by points this season{' with ' + format(ptd, 'g') + '-point passing touchdowns' if ptd else ''}.",
                 ["Player", "NFL", "Team", "Pts"], rows[:12])]


def firsts(C):
    rows, seen = [], set()
    marks = [(150, "First 150-point week"), (175, "First 175-point week")]
    for w in sorted(C.weeks):
        g = [x for x in C.games() if x[0] == w]
        for thr, label in marks:
            if label in seen:
                continue
            hits = [(a, pa) for _w, a, pa, b, pb in g if pa >= thr] + [(b, pb) for _w, a, pa, b, pb in g if pb >= thr]
            if hits:
                h, p = max(hits, key=lambda x: x[1])
                rows.append([label, T(h), f"Week {w}", _r1(p)])
                seen.add(label)
        lows = [(a, pa) for _w, a, pa, b, pb in g if pa < 70] + [(b, pb) for _w, a, pa, b, pb in g if pb < 70]
        if lows and "low" not in seen:
            h, p = min(lows, key=lambda x: x[1])
            rows.append(["First sub-70 week", T(h), f"Week {w}", _r1(p)])
            seen.add("low")
    rec = defaultdict(lambda: [0, 0])
    for w, a, pa, b, pb in sorted(C.games()):
        if pa == pb:
            continue
        win, lose = (a, b) if pa > pb else (b, a)
        rec[win][0] += 1
        rec[lose][1] += 1
        if rec[lose][1] == 1 and ("loss", lose) not in seen:
            seen.add(("loss", lose))
        if rec[win][0] == 1 and ("win", win) not in seen and w > 1:
            rows.append([f"First win, after an 0-{rec[win][1]} start", T(win), f"Week {w}", ""])
            seen.add(("win", win))
        if rec[win][0] == 5 and "five" not in seen:
            rows.append(["First to five wins", T(win), f"Week {w}", ""])
            seen.add("five")
    return [card("firsts", "Firsts log", "The season's milestones as they happen.",
                 ["Milestone", "Team", "When", "Pts"], rows)]


def beat_projection(C):
    """Started points against projections for those same starters, this season."""
    got, proj = defaultdict(float), defaultdict(float)
    for w, wk in C.weeks.items():
        try:
            pr = C.I._projections(C.season, w, C.cache_dir, C.read_json, C.write_json, final=True,
                                  shim_dir=C.shim_dir)
        except Exception:
            continue
        if not pr:
            continue
        for h, t in wk.items():
            for p in t["starters"]:
                got[h] += float(t["pp"].get(p, 0) or 0)
                proj[h] += C.score(pr.get(p)) or 0
    if not got:
        return []
    rows = sorted(([T(h), _r1(got[h]), _r1(proj[h]), _r1(got[h] - proj[h])] for h in got), key=lambda r: -r[3])
    src = "ESPN" if C.shim else "Sleeper"
    return [card("beatproj", f"Who beats {src}'s projections",
                 f"Points from started players this season against what {src} projected for those same players.",
                 ["Team", "Scored", "Projected", "Over / under"], rows)]


def trade_drama(C):
    """ESPN activity the trade page does not show. Cancelled offers and trades
    still in review stay off the public site (T.J.'s call), so only executed
    and vetoed trades are counted."""
    path = os.path.join(C.repo, "src", "lib", "data", "espn.json")
    e = C.read_json(path, None) or {}
    done, veto = defaultdict(int), defaultdict(int)
    for t in e.get("trade_attempts") or []:
        st = t.get("status")
        for side in t.get("sides") or []:
            if st == "executed":
                done[side.get("h")] += 1
            elif st == "vetoed":
                veto[side.get("h")] += 1
    dec = e.get("declines") or {}
    lost = defaultdict(int)
    for c in e.get("claims_failed") or []:
        lost[c.get("h")] += 1
    rows = []
    for h in C.teams:
        if done[h] or veto[h] or dec.get(h) or lost[h]:
            rows.append([T(h), done[h], veto[h], dec.get(h, 0), lost[h]])
    rows.sort(key=lambda r: -(r[1] * 3 + r[2] * 3 + r[3] + r[4]))
    return [card("drama", "Trade and waiver drama",
                 "From ESPN's league activity: trades that went through, trades the league vetoed, offers each team turned down, and waiver claims that missed.",
                 ["Team", "Trades", "Vetoed", "Offers turned down", "Claims missed"], rows)]


# ------------------------------------------------------------ build
# names_log on in every league (T.J., 2026-10-14: crude names are fine)
LEAGUE_SPECIALS = {
    "league-page": ["kicker_file", "board_duty", "draft_report", "names_log"],
    "league-fl-evolution": ["names_log"],
    "league-lets-go-brandon": ["names_log"],
    "league-megalabowl": ["median_misery", "qb_race", "firsts", "names_log"],
    "league-bound": ["trade_drama", "names_log"],
}


def _safe(fn, C):
    try:
        return fn(C)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"trackers: {fn.__name__} failed:", e)
        return []


def build_trackers(ctx, drafts=None, waivers=None):
    C = Ctx(ctx)
    drafts = drafts or (C.read_json(os.path.join(C.static, "drafts.json"), {}) or {})
    waivers = waivers or (C.read_json(os.path.join(C.static, "waivers.json"), {}) or {})
    C.drafts = drafts
    repo_name = os.path.basename(C.repo)
    fns = {f.__name__: f for f in (kicker_file, board_duty, draft_report, names_log,
                                     median_misery, qb_race, firsts, trade_drama)}
    groups = []

    def group(gid, title, intro, make):
        try:
            cards = [c for c in make() if c]
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"trackers: {gid} failed:", e)
            cards = []
        if cards:
            groups.append({"id": gid, "title": title, "intro": intro, "cards": cards})

    group("races", "Season races", "Who is winning the awards nobody hands out until December.",
          lambda: races(C, waivers, drafts) + beat_projection(C) + _safe(wire_flips, C))
    group("market", "Trade market", "Where the surplus is, where the holes are, and who should be talking.",
          lambda: trade_market(C))
    group("depth", "Bench and depth", "Depth wins the weeks nobody plans for.", lambda: bench(C))
    if C.dynasty:
        group("dynasty", "Dynasty desk", "This year, the next three drafts, and the clock on every roster.",
              lambda: dynasty(C))
    specials = LEAGUE_SPECIALS.get(repo_name, [])
    if specials:
        group("league", "Only in this league", "Trackers built for this league's own quirks.",
              lambda: [c for n in specials for c in _safe(fns[n], C)])
    doc = {"season": C.season, "through_week": C.last, "dynasty": C.dynasty,
           "projections": "ESPN" if C.shim else "Sleeper", "groups": groups}
    C.write_json(os.path.join(C.data, "trackers.json"), doc)
    return doc
