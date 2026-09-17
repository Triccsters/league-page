"""
update_site.py - weekly data refresh for a League Page site.

The same script runs both league sites. Per-league settings live in
scripts/site_config.json next to this file.

Writes static JSON the site reads (src/lib/data/):
  history.json          every game the league has played, managers, site info
  recaps/<season>-wNN.json  one recap per finished week (your title/intro/video/notes are kept)
  recaps/index.json     list of recaps, newest first
  managers.json         the Managers pages (edit manager_overrides.json, not this)
  rules.json            League Rules page (add your own rules in rules_extra.json)

Usage, from the repo root on tricclt:
  python scripts/update_site.py            refresh everything, write any new recaps
  python scripts/update_site.py --week 3   rebuild one week's recap
  python scripts/update_site.py --all      rebuild every week's recap
  python scripts/update_site.py --push     also git commit + push (Vercel redeploys)

History sources (site_config.json "history"):
  "vault"    FL Players: Yahoo 2014-2020 and Sleeper 2021-2025 from the vault's flp.py,
             the current season live from Sleeper.
  "sleeper"  every season read live from Sleeper, following previous_league_id.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

from build_rules import build_rules  # same folder
import extras  # same folder

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "src", "lib", "data")
RECAPS = os.path.join(DATA, "recaps")
STATIC = os.path.join(REPO, "static", "data")   # big files, fetched by the pages at runtime
OLD_SEASONS = []                                 # past Sleeper seasons read this run (sleeper mode)
CONFIG = json.load(open(os.path.join(REPO, "scripts", "site_config.json"), encoding="utf-8"))

LEAGUE_ID = CONFIG["league_id"]
SEASON = int(CONFIG["season"])
HISTORY_SOURCE = CONFIG.get("history", "sleeper")
VAULT_MANUAL = os.environ.get(
    "FLP_MANUAL", r"C:\Users\trick\Documents\Fantasy Football Vault\_manual")
PLAYER_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "league_page_players.json")

# Display-name renames that the vault data already folded together (FL Players).
CANON = {"Austin7Rock": "RockMNwild", "Tongueohvaeloa": "TuanonStan"}

# Real names, confirmed by T.J. 2026-09-08. Second value is the Yahoo name.
# Anyone not listed shows under their Sleeper display name.
MANAGERS = {
    "triccster": ("T.J.", "T.J.R"), "brettmn13": ("Brett", "Brett"),
    "Wallner": ("John Wallner", "John Wall"), "Colt45Johnson": ("Colt", "Colt"),
    "RockMNwild": ("Austin", "Austin"), "snelson91": ("Scott", "Scott"),
    "TuanonStan": ("James", "LordPmp"), "Jbird531": ("Joey", "Joey"),
    "YoungBuck04": ("Zak", "zak"), "butterygoop": ("Anthony", "Anthony"),
    "PapaMidnight": ("Mikey", "Mikey"), "thecreamer": ("Zach Nase", "zach"),
    "J Rock": ("J Rock", "J Rock"), "Tyler": ("Tyler", "Tyler"),
    "DJ": ("DJ", "DJ"), "Mitchell": ("Mitchell", "Mitchell"),
}

ELIG = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"}, "K": {"K"},
        "DEF": {"DEF"}, "FLEX": {"RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"},
        "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
SLOTS = ["Wed", "Thu", "Sun early", "Sun late", "SNF", "MNF"]
ESPN_ABBR = {"WSH": "WAS"}
REAL_ROUNDS = {"Quarterfinal", "Semifinal", "Championship"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "league-page-updater"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def sleeper(path):
    return get("https://api.sleeper.app/v1" + path)


def write_json(path, obj, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def real_name(handle):
    if handle.startswith("?"):          # Yahoo hid this manager; the key is the team name
        return handle[1:]
    return MANAGERS.get(handle, (handle,))[0]


def espn_week(week, season=SEASON):
    return get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
               f"scoreboard?week={week}&seasontype=2&dates={season}")


def week_is_final(week):
    try:
        evs = espn_week(week).get("events", [])
    except Exception:
        return False
    return bool(evs) and all(ev["status"]["type"].get("completed") for ev in evs)


# ---------------------------------------------------------------- one Sleeper season
class Season:
    """One Sleeper league-season. Handles are keyed on user_id, so a manager who
    changed display name keeps one identity (the current name)."""

    def __init__(self, league_id, handle_by_user=None):
        self.league_id = league_id
        self.league = sleeper(f"/league/{league_id}")
        self.season = int(self.league["season"])
        users = sleeper(f"/league/{league_id}/users") or []
        self.rosters = sleeper(f"/league/{league_id}/rosters") or []
        self.users = {u["user_id"]: u for u in users}
        hb = handle_by_user or {}
        name = lambda uid: hb.get(uid) or CANON.get(self.users[uid]["display_name"],
                                                    self.users[uid]["display_name"])
        self.owner = {r["roster_id"]: r["owner_id"] for r in self.rosters}
        self.handle = {rid: (name(oid) if oid in self.users else f"Roster {rid}")
                       for rid, oid in self.owner.items()}
        self.team_name = {uid: (u.get("metadata") or {}).get("team_name")
                          for uid, u in self.users.items()}
        self.slots = [s for s in self.league["roster_positions"] if s in ELIG]
        st = self.league.get("settings") or {}
        self.playoff_start = st.get("playoff_week_start") or 15
        self.two_week_final = st.get("playoff_round_type") == 1
        self._matchups = {}
        self._players = None

    def matchups(self, week):
        if week not in self._matchups:
            self._matchups[week] = sleeper(f"/league/{self.league_id}/matchups/{week}") or []
        return self._matchups[week]

    def pairs(self, week):
        by = defaultdict(list)
        for m in self.matchups(week):
            if m.get("matchup_id") is not None:
                by[m["matchup_id"]].append(m)
        return [v for v in by.values() if len(v) == 2]

    def completed_weeks(self, state):
        if self.league.get("status") == "complete" or str(state.get("season")) != str(self.season):
            weeks = []
            for w in range(1, 19):
                ms = self.matchups(w)
                if not ms or not any((m.get("points") or 0) > 0 for m in ms):
                    break
                weeks.append(w)
            return weeks
        cur = state.get("display_week") or state.get("week") or 1
        if state.get("season_type") != "regular":
            cur = 19
        weeks = list(range(1, min(cur, 18)))
        # Sleeper may not have moved to next week yet on Tuesday morning; if every
        # game of its current week is final on ESPN, that week is done too.
        if cur <= 18 and cur not in weeks and week_is_final(cur):
            weeks.append(cur)
        return weeks

    def playoff_labels(self):
        """(week, frozenset of roster ids) -> label, from Sleeper's brackets."""
        labels = {}
        wb = sleeper(f"/league/{self.league_id}/winners_bracket") or []
        lb = sleeper(f"/league/{self.league_id}/losers_bracket") or []
        top = max((g.get("r") or 0 for g in wb), default=0)
        for g in wb:
            r = g.get("r") or 0
            if g.get("p") == 1:
                name = "Championship"
            elif g.get("p"):
                name = f"{g['p']}{'rd' if g['p'] == 3 else 'th'} place"
            elif r == top - 1:
                name = "Semifinal"
            elif r == top - 2:
                name = "Quarterfinal"
            else:
                name = "Playoffs"
            key = frozenset((g.get("t1"), g.get("t2")))
            weeks = [self.playoff_start + r - 1]
            if r == top and self.two_week_final:
                weeks.append(weeks[0] + 1)
            for w in weeks:
                labels[(w, key)] = name
        for g in lb:
            r = g.get("r") or 0
            labels[(self.playoff_start + r - 1, frozenset((g.get("t1"), g.get("t2"))))] = "Consolation"
        return labels

    def games(self, weeks):
        labels = self.playoff_labels() if any(w >= self.playoff_start for w in weeks) else {}
        out = []
        for wk in weeks:
            playoff = wk >= self.playoff_start
            for a, b in self.pairs(wk):
                label = None
                if playoff:
                    label = labels.get((wk, frozenset((a["roster_id"], b["roster_id"]))), "Consolation")
                out.append([self.season, wk, "sleeper",
                            self.handle[a["roster_id"]], round(a.get("points") or 0, 2),
                            self.handle[b["roster_id"]], round(b.get("points") or 0, 2),
                            playoff, label])
        return out

    # players ------------------------------------------------------------
    @property
    def players(self):
        if self._players is None:
            age = None
            if os.path.exists(PLAYER_CACHE):
                age = datetime.now().timestamp() - os.path.getmtime(PLAYER_CACHE)
            if age is None or age > 3 * 86400:
                self._players = sleeper("/players/nfl")
                os.makedirs(os.path.dirname(PLAYER_CACHE), exist_ok=True)
                with open(PLAYER_CACHE, "w", encoding="utf-8") as f:
                    json.dump(self._players, f)
            else:
                with open(PLAYER_CACHE, encoding="utf-8") as f:
                    self._players = json.load(f)
        return self._players

    def pinfo(self, pid):
        p = self.players.get(pid) or {}
        if not p and not pid.isdigit():          # team defence: the id is the team
            return {"name": f"{pid} DEF", "pos": "DEF", "team": pid}
        name = p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        return {"name": name or pid, "pos": p.get("position") or "?", "team": p.get("team")}


# ---------------------------------------------------------------- history
def build_history(cur, state):
    games = []
    team_names = defaultdict(dict)       # season -> handle -> team name
    if HISTORY_SOURCE == "vault":
        sys.path.insert(0, VAULT_MANUAL)
        import flp  # noqa: E402  (vault data layer)
        import yahoo_pre2014  # noqa: E402  (2008, 2010, 2012, 2013)
        import yahoo_standings as YS  # noqa: E402
        games += yahoo_pre2014.games()
        for season, names in yahoo_pre2014.team_names().items():
            team_names[season].update(names)
        for season, teams in YS.TEAM_TO_MANAGER.items():
            for team, first in teams.items():
                team_names[int(season)][flp.person(first)] = team
        for season in flp.SLEEPER_SEASONS:
            try:
                blob = flp._sleeper_blob(season)
            except OSError:
                continue
            for u in blob["users"]:
                h = flp.CANON_SLEEPER.get(u["display_name"], u["display_name"])
                team_names[season][h] = (u.get("metadata") or {}).get("team_name") or u["display_name"]
        for g in flp.games():
            if g.season >= SEASON:
                continue
            games.append([g.season, g.week, g.era, g.a, round(g.pa, 2),
                          g.b, round(g.pb, 2), bool(g.playoff), g.label])
    else:
        # Walk back through Sleeper. Current display names win for every season.
        handle_by_user = {uid: CANON.get(u["display_name"], u["display_name"])
                          for uid, u in cur.users.items()}
        prev = cur.league.get("previous_league_id")
        while prev and prev != "0":
            old = Season(prev, handle_by_user)
            for uid, u in old.users.items():
                handle_by_user.setdefault(uid, CANON.get(u["display_name"], u["display_name"]))
            old = Season(prev, handle_by_user)
            games = old.games(old.completed_weeks(state)) + games
            OLD_SEASONS.append(old)
            for rid, h in old.handle.items():
                team_names[old.season][h] = old.team_name.get(old.owner.get(rid)) or h
            print(f"  {old.season}: read from Sleeper")
            prev = old.league.get("previous_league_id")
    games += cur.games(cur.completed_weeks(state))
    games.sort(key=lambda g: (g[0], g[1]))
    for rid, h in cur.handle.items():
        team_names[cur.season][h] = cur.team_name.get(cur.owner.get(rid)) or h
    played = {g[0] for g in games}

    people = sorted({g[3] for g in games} | {g[5] for g in games} | set(cur.handle.values()))
    managers = {h: {"name": real_name(h),
                    "yahoo": MANAGERS[h][1] if h in MANAGERS and HISTORY_SOURCE == "vault" else None,
                    "hidden": h.startswith("?")}
                for h in people}
    eras = sorted({g[2] for g in games})
    out = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site": {
            "league_name": cur.league.get("name", "").strip(),
            "season": SEASON,
            "first_season": min((g[0] for g in games), default=SEASON),
            "eras": eras,
            "yahoo_years": ([min(g[0] for g in games if g[2] == "yahoo"),
                             max(g[0] for g in games if g[2] == "yahoo")]
                            if "yahoo" in eras else None),
            "sleeper_from": min((g[0] for g in games if g[2] == "sleeper"), default=SEASON),
            "missing_seasons": [y for y in range(min(played, default=SEASON), SEASON) if y not in played],
        },
        "team_names": {str(k): v for k, v in sorted(team_names.items())},
        "fields": ["season", "week", "era", "a", "pa", "b", "pb", "playoff", "label"],
        "managers": managers,
        "current": sorted(set(cur.handle.values())),
        "games": games,
    }
    write_json(os.path.join(DATA, "history.json"), out)
    return out


# ---------------------------------------------------------------- recap
def kickoff_slots(week):
    """Team abbreviation -> Wed/Thu/Sun early/Sun late/SNF/MNF from ESPN."""
    out = {}
    for ev in espn_week(week).get("events", []):
        # ESPN dates are UTC; shift to US Central (CDT, close enough for naming windows).
        t = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        c = datetime.fromtimestamp(t.timestamp() - 5 * 3600, timezone.utc)
        wd, hr = c.weekday(), c.hour           # Mon=0 ... Sun=6
        if wd == 2:
            slot = "Wed"
        elif wd in (3, 4, 5):
            slot = "Thu"
        elif wd == 6 and hr < 14:
            slot = "Sun early"
        elif wd == 6 and hr < 18:
            slot = "Sun late"
        elif wd == 6:
            slot = "SNF"
        else:
            slot = "MNF"
        for comp in ev["competitions"][0]["competitors"]:
            ab = comp["team"]["abbreviation"]
            out[ESPN_ABBR.get(ab, ab)] = slot
    return out


def optimal(season, pp, roster):
    order = sorted(season.slots, key=lambda s: len(ELIG[s]))
    used, total = set(), 0.0
    for s in order:
        best = None
        for p in roster:
            if p in used or season.pinfo(p)["pos"] not in ELIG[s]:
                continue
            if best is None or pp.get(p, 0) > pp.get(best, 0):
                best = p
        if best:
            used.add(best)
            total += pp.get(best, 0)
    return round(total, 2)


_STARTS = {}


def starter_points(season, state):
    """(handle, player_id) -> {week: points} for every week that player was started.

    Built once per season so a recap can compare a starter's week against his own
    normal output for that manager.
    """
    key = id(season)
    if key not in _STARTS:
        out = defaultdict(dict)
        for w in season.completed_weeks(state):
            for mm in season.matchups(w):
                h = season.handle.get(mm.get("roster_id"))
                if not h:
                    continue
                pp = mm.get("players_points") or {}
                for p in (mm.get("starters") or []):
                    if p and p != "0":
                        out[(h, p)][w] = round(pp.get(p, 0) or 0, 2)
        _STARTS[key] = out
    return _STARTS[key]


def shortfalls(season, m, week, hist):
    """Starters who came in under their own normal, worst first.

    A player needs two other starts for that manager this season before there is
    anything to compare against, so early weeks return little and say nothing.
    """
    h = season.handle.get(m.get("roster_id"))
    pp = m.get("players_points") or {}
    out = []
    for p in (m.get("starters") or []):
        if not p or p == "0":
            continue
        weeks = hist.get((h, p), {})
        other = [v for w, v in weeks.items() if w != week]
        if len(other) < 2:
            continue
        avg = sum(other) / len(other)
        got = round(pp.get(p, 0) or 0, 2)
        if avg - got <= 0:
            continue
        info = season.pinfo(p)
        out.append({"name": info["name"], "pos": info["pos"], "pts": got,
                    "avg": round(avg, 2), "short": round(avg - got, 2)})
    out.sort(key=lambda x: -x["short"])
    return out


def side(season, m, slot_of):
    pts = round(m.get("points") or 0, 2)
    pp = m.get("players_points") or {}
    starters = [p for p in (m.get("starters") or []) if p and p != "0"]
    run = {s: 0.0 for s in SLOTS}
    by_pos = defaultdict(float)
    for p, v in zip(m.get("starters") or [], m.get("starters_points") or []):
        if not p or p == "0":
            continue
        info = season.pinfo(p)
        by_pos[info["pos"]] += v or 0
        s = slot_of.get(info["team"])
        if s:
            run[s] += v or 0
    tl, acc = [], 0.0
    for s in SLOTS:
        acc += run[s]
        tl.append(round(acc, 2))
    bench = [p for p in (m.get("players") or []) if p not in starters]
    best_bench = max(bench, key=lambda p: pp.get(p, 0), default=None)
    worst_start = min(starters, key=lambda p: pp.get(p, 0), default=None)
    opt = optimal(season, pp, m.get("players") or [])
    rid = m["roster_id"]
    return {
        "manager": season.handle[rid],
        "team": season.team_name.get(season.owner.get(rid)),
        "points": pts,
        "optimal": opt,
        "left_on_bench": round(max(0.0, opt - pts), 2),
        "timeline": tl,
        "by_pos": {k: round(v, 2) for k, v in sorted(by_pos.items())},
        "top": sorted(({"name": season.pinfo(p)["name"], "pos": season.pinfo(p)["pos"],
                        "pts": round(pp.get(p, 0), 2)} for p in starters),
                      key=lambda x: -x["pts"])[:3],
        "best_bench": best_bench and {"name": season.pinfo(best_bench)["name"],
                                      "pts": round(pp.get(best_bench, 0), 2)},
        "worst_start": worst_start and {"name": season.pinfo(worst_start)["name"],
                                        "pts": round(pp.get(worst_start, 0), 2)},
    }


def record_through(history, week):
    rec = defaultdict(lambda: [0, 0, 0, 0.0])
    for s, w, _e, a, pa, b, pb, playoff, _l in history["games"]:
        if s != SEASON or w > week or playoff:
            continue
        for me, mp, op in ((a, pa, pb), (b, pb, pa)):
            r = rec[me]
            r[3] += mp
            r[0 if mp > op else 1 if mp < op else 2] += 1
    rows = [{"manager": m, "w": r[0], "l": r[1], "t": r[2], "pf": round(r[3], 2)}
            for m, r in rec.items()]
    rows.sort(key=lambda x: (-x["w"], -x["pf"]))
    return rows


def h2h_line(history, a, b, before):
    """All-time record between a and b before this season-week."""
    wa = wb = 0
    for s, w, _e, x, px, y, py, _p, _l in history["games"]:
        if (s, w) >= before or {x, y} != {a, b}:
            continue
        winner = x if px > py else y if py > px else None
        wa += winner == a
        wb += winner == b
    return [wa, wb]


def build_recap(season, history, week, state):
    path = os.path.join(RECAPS, f"{SEASON}-w{week:02d}.json")
    old = read_json(path, {}) or {}
    slot_of = kickoff_slots(week)
    hist = starter_points(season, state)
    games = []
    for a, b in season.pairs(week):
        sa, sb = side(season, a, slot_of), side(season, b, slot_of)
        ma, mb = a, b
        if sb["points"] > sa["points"]:
            sa, sb = sb, sa
            ma, mb = b, a
        margin = round(sa["points"] - sb["points"], 2)
        # who came in under their own normal, and whether that alone explains the loss
        short_l = shortfalls(season, mb, week, hist)
        short_w = shortfalls(season, ma, week, hist)
        games.append({"winner": sa, "loser": sb,
                      "margin": margin,
                      "cost": [s for s in short_l[:3]],
                      "cost_decisive": [s for s in short_l if s["short"] >= margin][:2],
                      "won_despite": [s for s in short_w[:2] if s["avg"] and s["pts"] < s["avg"] / 2],
                      "h2h_before": h2h_line(history, sa["manager"], sb["manager"],
                                             (SEASON, week))})
    games.sort(key=lambda g: g["margin"])
    everyone = [s for g in games for s in (g["winner"], g["loser"])]
    top_player = max(({"manager": s["manager"], **t} for s in everyone for t in s["top"]),
                     key=lambda x: x["pts"], default=None)
    regret = max(everyone, key=lambda s: s["left_on_bench"], default=None)
    high = max(everyone, key=lambda s: s["points"], default=None)
    low = min(everyone, key=lambda s: s["points"], default=None)
    pts = sorted(s["points"] for s in everyone)
    median = round((pts[len(pts) // 2] + pts[(len(pts) - 1) // 2]) / 2, 2) if pts else 0

    # weekly awards: the same week read as a short list of titles
    winners = [g["winner"] for g in games]
    losers = [g["loser"] for g in games]
    lucky = min(winners, key=lambda s: s["points"], default=None)
    unlucky = max(losers, key=lambda s: s["points"], default=None)

    def eff(s):
        return (s["points"] / s["optimal"]) if s.get("optimal") else 0

    sharp = max(everyone, key=eff, default=None)
    awards = []

    def award(key, emoji, name, s, value, note=None, vs=None):
        if s:
            awards.append({"key": key, "emoji": emoji, "name": name,
                           "manager": s["manager"], "value": value, "note": note, "vs": vs})

    award("high", "🏆", "Team of the week", high, high and high["points"])
    award("top_player", "🔥", "Player of the week",
          top_player and {"manager": top_player["manager"]}, top_player and top_player["pts"],
          top_player and top_player.get("name"))
    if sharp and eff(sharp) > 0:
        award("sharp", "🎯", "Best lineup call", sharp, "%d%%" % round(100 * eff(sharp)),
              "scored %s of a possible %s" % (sharp["points"], sharp["optimal"]))
    if lucky and lucky["points"] < median:
        award("lucky", "🍀", "Won anyway", lucky, lucky["points"],
              "below the week's median of %s" % median)
    if unlucky and unlucky["points"] > median:
        award("unlucky", "🥀", "Lost anyway", unlucky, unlucky["points"],
              "above the week's median of %s" % median)
    if regret and regret.get("left_on_bench"):
        bb = regret.get("best_bench") or {}
        note = ("%s scored %s on his bench" % (bb.get("name"), bb.get("pts"))) if bb.get("name") else None
        award("bench", "🪑", "Left on the bench", regret, regret["left_on_bench"], note)
    award("low", "💤", "Quietest week", low, low and low["points"])
    if games:
        c, b = games[0], games[-1]
        award("closest", "😬", "Closest game", c["winner"], c["margin"],
              vs=c["loser"]["manager"])
        award("blowout", "💀", "Biggest blowout", b["winner"], b["margin"],
              vs=b["loser"]["manager"])

    recap = {
        "season": SEASON, "week": week,
        "slug": f"{SEASON}-w{week:02d}",
        "title": old.get("title") or f"Week {week} recap",
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Hand-written fields: the script never overwrites these.
        "intro": old.get("intro", ""),
        "video": old.get("video", ""),
        "notes": old.get("notes", []),
        "slots": SLOTS,
        "median": median,
        "awards": awards,
        "scores": sorted(({"manager": s["manager"], "points": s["points"],
                           "optimal": s["optimal"]} for s in everyone),
                         key=lambda x: -x["points"]),
        "games": games,
        "facts": {
            "closest": games[0] if games else None,
            "blowout": games[-1] if games else None,
            "high": high and {"manager": high["manager"], "points": high["points"]},
            "low": low and {"manager": low["manager"], "points": low["points"]},
            "top_player": top_player,
            "bench_regret": regret and {"manager": regret["manager"],
                                        "points": regret["left_on_bench"],
                                        "best_bench": regret["best_bench"]},
        },
        "standings": record_through(history, week),
    }
    write_json(path, recap)
    return recap


def build_index():
    items = []
    for fn in sorted(os.listdir(RECAPS), reverse=True):
        if not fn.endswith(".json") or fn == "index.json":
            continue
        r = read_json(os.path.join(RECAPS, fn))
        items.append({"slug": r["slug"], "season": r["season"], "week": r["week"],
                      "title": r["title"], "video": bool(r.get("video"))})
    write_json(os.path.join(RECAPS, "index.json"), items)
    return items


# ---------------------------------------------------------------- managers
def build_managers(cur, history):
    """managers.json for the Managers pages. Anything in manager_overrides.json
    (keyed by Sleeper handle) replaces the generated value."""
    overrides = read_json(os.path.join(DATA, "manager_overrides.json"), {}) or {}
    handle_of = {cur.owner[r]: h for r, h in cur.handle.items() if r in cur.owner}
    users = [u for uid, u in cur.users.items() if uid in handle_of]
    order = sorted(users, key=lambda u: real_name(handle_of[u["user_id"]]).lower())
    index = {handle_of[u["user_id"]]: i for i, u in enumerate(order)}

    out = []
    for u in order:
        h = handle_of[u["user_id"]]
        name = real_name(h)
        w = l = 0
        titles, finals, seasons = [], 0, set()
        vs = defaultdict(lambda: [0, 0])
        for s, _wk, _e, a, pa, b, pb, playoff, label in history["games"]:
            if h not in (a, b):
                continue
            me, opp = (pa, pb) if a == h else (pb, pa)
            other = b if a == h else a
            seasons.add(s)
            if not playoff:
                w += me > opp
                l += me < opp
            if label == "Championship":
                finals += 1
                if me > opp:
                    titles.append(s)
            if not playoff or label in REAL_ROUNDS:
                vs[other][0 if me > opp else 1] += 1
        foes = [o for o in vs if o in index and o != h]
        nemesis = max(foes, key=lambda o: (vs[o][1] - vs[o][0], vs[o][1]), default=None)
        bits = [f"Regular season since {min(seasons)}: {w}-{l}." if seasons else "No games yet."]
        if titles:
            bits.append(f"Champion: {', '.join(map(str, titles))}.")
        elif finals:
            bits.append(f"{finals} final{'s' if finals > 1 else ''}, still chasing a title.")
        elif seasons:
            bits.append("Still chasing a first title.")
        if nemesis:
            nw, nl = vs[nemesis]
            bits.append(f"Toughest opponent: {real_name(nemesis)} ({nw}-{nl}).")
        bio = " ".join(bits)
        if nemesis:
            bio += f' <a href="/rivalries/{"--".join(sorted([h, nemesis]))}">That rivalry</a> ·'
        bio += f' <a href="/rivalries?who={h}">All of {name}\'s rivalries</a>'
        entry = {
            "managerID": u["user_id"],
            "handle": h,
            "name": name,
            "photo": (f"https://sleepercdn.com/avatars/{u['avatar']}" if u.get("avatar")
                      else "/managers/question.jpg"),
            "fantasyStart": min(seasons) if seasons else None,
            "bio": bio,
            "rival": {
                "name": real_name(nemesis) if nemesis else "Everyone",
                "link": index.get(nemesis) if nemesis else None,
                "image": "/managers/everyone.png",
            },
        }
        entry.update(overrides.get(h, {}))
        out.append(entry)
    for e in out:   # rival photo follows the rival's (possibly overridden) photo
        if e["rival"]["link"] is not None:
            e["rival"]["image"] = out[e["rival"]["link"]]["photo"]
    write_json(os.path.join(DATA, "managers.json"), out)
    if not os.path.exists(os.path.join(DATA, "manager_overrides.json")):
        write_json(os.path.join(DATA, "manager_overrides.json"), {
            "_how_to": "Key by Sleeper handle. Any field set here replaces the generated one, "
                       "e.g. \"triccster\": {\"bio\": \"...\", \"photo\": \"/managers/tj.jpg\", "
                       "\"favoriteTeam\": \"min\", \"location\": \"Maplewood\"}"})
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, help="rebuild just this week's recap")
    ap.add_argument("--all", action="store_true", help="rebuild every finished week")
    ap.add_argument("--push", action="store_true", help="git commit and push")
    args = ap.parse_args()

    state = sleeper("/state/nfl")
    cur = Season(LEAGUE_ID)
    history = build_history(cur, state)
    print(f"history.json: {len(history['games'])} games "
          f"({sum(1 for g in history['games'] if g[0] == SEASON)} from {SEASON})")

    done = cur.completed_weeks(state)
    if args.week:
        weeks = [args.week]
    elif args.all:
        weeks = done
    else:   # weeks without a recap yet, plus the latest (scores can be corrected)
        weeks = [w for w in done
                 if not os.path.exists(os.path.join(RECAPS, f"{SEASON}-w{w:02d}.json"))]
        if done and done[-1] not in weeks:
            weeks.append(done[-1])
    os.makedirs(RECAPS, exist_ok=True)
    for w in weeks:
        r = build_recap(cur, history, w, state)
        print(f"recap week {w}: {len(r['games'])} games")
    build_index()
    print(f"managers.json: {len(build_managers(cur, history))} managers")
    rules = build_rules(LEAGUE_ID, sleeper, os.path.join(DATA, "rules_extra.json"),
                        os.path.join(DATA, "rules.json"), write_json, read_json)
    print(f"rules.json: {sum(len(h['changes']) for h in rules['history'])} rule changes "
          f"since {rules['first_sleeper_season']}")

    ctx = {"mode": HISTORY_SOURCE, "cur": cur, "state": state, "history": history, "season": SEASON,
           "live_seasons": sorted(OLD_SEASONS, key=lambda x: x.season) + [cur],
           "dynasty": (cur.league.get("settings") or {}).get("type") == 2,
           "odds_prior": CONFIG.get("odds_prior"),   # "current" (redraft default) or "last_season"
           "data": DATA, "static": STATIC, "vault_manual": VAULT_MANUAL,
           "write_json": write_json, "read_json": read_json, "sleeper": sleeper}
    print("extras:", extras.build_all(ctx))

    if args.push:
        subprocess.run(["git", "-C", REPO, "add", "src/lib/data", "static/data"], check=True)
        diff = subprocess.run(["git", "-C", REPO, "diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            print("nothing changed, no push")
            return
        msg = f"Data refresh: {SEASON} through week {done[-1] if done else 0}"
        subprocess.run(["git", "-C", REPO, "commit", "-m", msg], check=True)
        subprocess.run(["git", "-C", REPO, "push"], check=True)
        print("pushed; Vercel will redeploy")


if __name__ == "__main__":
    main()
