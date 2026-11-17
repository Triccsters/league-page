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
# "Triccster": T.J. capitalised his Sleeper name on 2026-11-14. Every stored file, page
# address and vault script knows him by the old key, so the key stays and SHOWN carries
# the new spelling onto the pages.
CANON = {"Austin7Rock": "RockMNwild", "Tongueohvaeloa": "TuanonStan", "Triccster": "triccster"}

# Sites that show Sleeper usernames (site_config "names": "handles"): the name to print
# when it differs from the stored key, and the last issue written under the old spelling.
# Issues and recaps up to that slug keep showing the old one.
SHOWN = {"triccster": ("Triccster", "2026-w09")}

# Real names, confirmed by T.J. 2026-09-08; John, Buckley, Nase per T.J. 2026-10-14. Second value is the Yahoo name.
# Anyone not listed shows under their Sleeper display name.
MANAGERS = {
    "triccster": ("T.J.", "T.J.R"), "brettmn13": ("Brett", "Brett"),
    "Wallner": ("John", "John Wall"), "Colt45Johnson": ("Colt", "Colt"),
    "RockMNwild": ("Austin", "Austin"), "snelson91": ("Scott", "Scott"),
    "TuanonStan": ("James", "LordPmp"), "Jbird531": ("Joey", "Joey"),
    "YoungBuck04": ("Buckley", "zak"), "butterygoop": ("Anthony", "Anthony"),
    "PapaMidnight": ("Mikey", "Mikey"), "thecreamer": ("Nase", "zach"),
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
    # A shimmed league (League Bound is on ESPN) has no Sleeper league or
    # draft to call: espn_shim.py writes Sleeper-shaped copies under
    # static/shim/v1/ and we read those instead. Everything else - NFL
    # state, the player index, projections - is still really Sleeper.
    if CONFIG.get("shim") and path.startswith(("/league/", "/draft/")):
        f = os.path.join(REPO, "static", "shim", "v1", path.strip("/") + ".json")
        return read_json(f, None)
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
    # site_config "names": "handles" shows everyone by Sleeper username
    # (FL Evolution, T.J.'s call 2026-09-30); default is the real-name map
    if CONFIG.get("names") == "handles":
        return SHOWN.get(handle, (handle,))[0]
    return MANAGERS.get(handle, (handle,))[0]


def espn_week(week, season=SEASON):
    return get("https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/"
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
        # stripped: managers type these into Sleeper and a stray leading space
        # renders as an indent on the site. An all-whitespace name becomes None
        # so the display falls back to the handle rather than showing a gap.
        self.team_name = {uid: (((u.get("metadata") or {}).get("team_name") or "").strip() or None)
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
                h = flp.handle_for(u)
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
    if CONFIG.get("names") == "handles":
        for h, (_now, through) in SHOWN.items():
            if h in managers:
                managers[h]["was"] = {"name": h, "through": through}
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
BAD_LINEUPS = []


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
    if opt + 0.01 < pts:
        # The best lineup can never score less than the one that was played.
        # When it does, the player positions behind it are wrong (League Bound,
        # 2026-10-13: 152 ESPN players read as defences), so stop the push.
        BAD_LINEUPS.append(f"{season.handle.get(m['roster_id'])} played {pts}, best lineup {opt}")
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
                        "id": p, "nfl": season.pinfo(p)["team"],
                        "pts": round(pp.get(p, 0), 2)} for p in starters),
                      key=lambda x: -x["pts"])[:3],
        "best_bench": best_bench and {"name": season.pinfo(best_bench)["name"],
                                      "id": best_bench, "nfl": season.pinfo(best_bench)["team"],
                                      "pts": round(pp.get(best_bench, 0), 2)},
        "worst_start": worst_start and {"name": season.pinfo(worst_start)["name"],
                                        "id": worst_start, "nfl": season.pinfo(worst_start)["team"],
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
def _img(a):
    """Sleeper stores an avatar id; the ESPN shim stores a full URL."""
    if not a:
        return None
    return a if str(a).startswith("http") else f"https://sleepercdn.com/avatars/{a}"


def _career(h, games):
    """One handle's career from history["games"]: regular-season record, titles, finals
    reached, seasons played, and the head-to-head table. Used for the current managers
    and for the past managers appended after them, so the two cannot drift apart."""
    w = l = 0
    titles, finals, seasons = [], 0, set()
    vs = defaultdict(lambda: [0, 0])
    for s, _wk, _e, a, pa, b, pb, playoff, label in games:
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
    return w, l, titles, finals, seasons, vs


def build_managers(cur, history):
    """managers.json for the Managers pages. Anything in manager_overrides.json
    (keyed by Sleeper handle) replaces the generated value. Managers listed in
    past_managers.json are appended: they are in history but not in the league."""
    overrides = read_json(os.path.join(DATA, "manager_overrides.json"), {}) or {}
    handle_of = {cur.owner[r]: h for r, h in cur.handle.items() if r in cur.owner}
    users = [u for uid, u in cur.users.items() if uid in handle_of]
    order = sorted(users, key=lambda u: real_name(handle_of[u["user_id"]]).lower())
    index = {handle_of[u["user_id"]]: i for i, u in enumerate(order)}

    out = []
    for u in order:
        h = handle_of[u["user_id"]]
        name = real_name(h)
        w, l, titles, finals, seasons, vs = _career(h, history["games"])
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
            "photo": _img(u.get("avatar")) or "/managers/question.jpg",
            # the team's avatar in this league (Sleeper team photo, ESPN team logo),
            # falling back to the manager's own photo
            "avatar": (u.get("metadata") or {}).get("avatar") or _img(u.get("avatar")) or "/managers/question.jpg",
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
    out += _past_managers(history, index)
    write_json(os.path.join(DATA, "managers.json"), out)
    if not os.path.exists(os.path.join(DATA, "manager_overrides.json")):
        write_json(os.path.join(DATA, "manager_overrides.json"), {
            "_how_to": "Key by Sleeper handle. Any field set here replaces the generated one, "
                       "e.g. \"triccster\": {\"bio\": \"...\", \"photo\": \"/managers/tj.jpg\", "
                       "\"favoriteTeam\": \"min\", \"location\": \"Maplewood\"}"})
    return out


def _slug(s):
    out = "".join(c.lower() if c.isalnum() else "-" for c in str(s))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def _team_name(history, season, h):
    tn = history.get("team_names") or {}
    return (tn.get(season) or tn.get(str(season)) or {}).get(h)


def _past_managers(history, index):
    """Manager pages for people in history who are not in the current league.

    past_managers.json is keyed by the handle history uses, and carries only what cannot
    be computed: {"id": "past-j-rock", "name": "J Rock"} plus any field to override.
    `id` becomes the manager page's permanent address (?manager=<id>), so it must never
    change once a link has been shared. Everything else - record, titles, seasons, last
    team - is recomputed from history.json on every build.

    Appended after the current managers so their rival links, which are indices into
    managers.json, keep pointing at the same people. Hidden handles (the teams whose
    manager was never identified) are refused here; they belong in unclaimed.json.
    """
    cfgs = read_json(os.path.join(DATA, "past_managers.json"), {}) or {}
    hidden = {h for h, m in (history.get("managers") or {}).items() if m.get("hidden")}
    played = {g[3] for g in history["games"]} | {g[5] for g in history["games"]}
    out = []
    # drop "_how_to" and anything malformed BEFORE sorting: the sort key reads the
    # config, and a string value there has no .get
    real = [(h, c) for h, c in cfgs.items() if not h.startswith("_") and isinstance(c, dict)]
    for h, cfg in sorted(real, key=lambda kv: str(kv[1].get("name") or kv[0]).lower()):
        if not cfg.get("id"):
            print(f"  past_managers.json: {h} has no id, skipped")
            continue
        if h in index:
            print(f"  past_managers.json: {h} is in the current league, skipped")
            continue
        if h in hidden:
            print(f"  past_managers.json: {h} is an unidentified team, belongs in unclaimed.json, skipped")
            continue
        if h not in played:
            print(f"  past_managers.json: {h} has no games in history, skipped")
            continue
        w, l, titles, finals, seasons, vs = _career(h, history["games"])
        name = cfg.get("name") or real_name(h)
        last = max(seasons)
        foes = [o for o in vs if o not in hidden and o != h]
        nemesis = max(foes, key=lambda o: (vs[o][1] - vs[o][0], vs[o][1]), default=None)
        span = f"in {last}" if min(seasons) == last else f"from {min(seasons)} to {last}"
        bits = [f"Played {span}. Regular season: {w}-{l}."]
        if titles:
            bits.append(f"Champion: {', '.join(map(str, titles))}.")
        elif finals:
            bits.append(f"{finals} final{'s' if finals > 1 else ''}, never won one.")
        if nemesis:
            nw, nl = vs[nemesis]
            bits.append(f"Toughest opponent: {real_name(nemesis)} ({nw}-{nl}).")
        bits.append("No longer in the league.")
        entry = {
            "managerID": str(cfg["id"]),
            "handle": h,
            "name": name,
            "photo": cfg.get("photo") or "/managers/question.jpg",
            "avatar": cfg.get("photo") or "/managers/question.jpg",
            "fantasyStart": min(seasons),
            "bio": " ".join(bits),
            # read by Manager.svelte: a past manager has no roster, no entry in
            # leagueTeamManagers and no transactions, so those sections are skipped
            "past": True,
            "lastSeason": last,
            "lastTeamName": _team_name(history, last, h),
            "seasonsPlayed": sorted(seasons),
            "rival": {"name": real_name(nemesis) if nemesis else "Everyone",
                      "link": None, "image": "/managers/everyone.png"},
        }
        entry.update({k: v for k, v in cfg.items() if k != "id"})
        out.append(entry)
    return out


def _team_key(s):
    """Team names for matching. Yahoo's pages use curly apostrophes and history.json
    straight ones, so "Hurst Don't It" and "Hurst Don’t It" are the same team.
    Fold the quote characters and the spacing rather than hard-coding either form."""
    s = (s or "").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    return " ".join(s.split()).casefold()


def build_vetoed(history, vault_manual):
    """vetoed_trades.json: trades the league killed, from the Yahoo years.

    Source is the vault's _yahoo_vetoed_trades.json, read 2026-11-16 from Yahoo's
    transaction log (Trades filter) for 2008/2010/2012/2013 and from the archived
    2016_transactions.csv. Ten exist in all - nine in 2012, one in 2016 - and that
    is the complete set for every Yahoo season the league ran.

    Only the vault has the source file, so a build without it LEAVES THE COMMITTED
    FILE ALONE rather than writing an empty one. That is why there is no `or {}`
    fallback here: an absent vault must not look like "no vetoed trades".

    Team names resolve to handles through history's team_names, which covers every
    season, so the 2016 entry works the same way as the pre-2014 ones.
    """
    src = read_json(os.path.join(vault_manual, "_yahoo_vetoed_trades.json"), None)
    if not src:
        return "no vault file, kept what is committed"

    names = history.get("team_names") or {}

    def handle_for(season, team):
        want = _team_key(team)
        for key in (season, str(season)):
            for h, v in (names.get(key) or {}).items():
                if _team_key(v) == want:
                    return h
        return None

    trades, by_mgr, by_season = [], defaultdict(int), defaultdict(int)
    unresolved = []
    for t in src.get("vetoed") or []:
        season, sides = t["season"], []
        for s in t["sides"]:
            h = handle_for(season, s["team"])
            if h is None:
                unresolved.append(f'{t["id"]} {s["team"]}')
            else:
                by_mgr[h] += 1
            sides.append({"handle": h, "name": real_name(h) if h else None,
                          "team": s["team"], "got": s["got"]})
        by_season[season] += 1
        row = {"id": t["id"], "season": season, "when": t["when"], "sides": sides}
        for extra in ("resubmitted", "lore"):
            if t.get(extra):
                row[extra] = t[extra]
        trades.append(row)

    write_json(os.path.join(DATA, "vetoed_trades.json"), {
        "count": len(trades),
        "bySeason": {str(k): v for k, v in sorted(by_season.items())},
        "byManager": dict(sorted(by_mgr.items(), key=lambda kv: -kv[1])),
        "trades": trades,
        "note": src.get("coverage", ""),
    })
    msg = f"{len(trades)} vetoed trades"
    if unresolved:
        msg += f" - UNRESOLVED TEAM NAMES: {', '.join(unresolved)}"
    return msg


def build_yahoo_history(history, vault_manual):
    """yahoo_history.json: the Yahoo-era league history that was on no page here.

    Three things, all from the vault's _yahoo_league_history.json, which was read off
    Yahoo's own Managers pages and Commish Updates logs on 2026-11-16:

      activity   waiver priority, moves, trades and FAAB left, per team per season,
                 for all eleven Yahoo seasons. Nothing on the site carried pre-2014
                 activity at all.
      settings   the dated commissioner changes - half PPR arriving in 2018, trade
                 review moving from a league vote to the commissioner, division
                 winners taking the top playoff seeds from 2012, fractional points
                 from 2013. rules.json only ever covered 2021 onward.
      trades     the 44 trades from 2008-2013. trades.json starts at 2014 because the
                 vault has no pre-2014 lineups, so these carry no value or winner -
                 who got whom, and when, and nothing invented on top.

    Same contract as build_vetoed: no vault file means the committed file is LEFT
    ALONE, so a build elsewhere cannot blank it.
    """
    src = read_json(os.path.join(vault_manual, "_yahoo_league_history.json"), None)
    if not src:
        return "no vault file, kept what is committed"

    names = history.get("team_names") or {}

    def handle_for(season, team):
        want = _team_key(team)
        for key in (season, str(season)):
            for h, v in (names.get(key) or {}).items():
                if _team_key(v) == want:
                    return h
        return None

    unresolved = []
    activity = {}
    for season, teams in sorted((src.get("activity") or {}).items()):
        rows = []
        for team, a in teams.items():
            h = handle_for(int(season), team)
            if h is None:
                unresolved.append(f"activity {season} {team}")
            rows.append({"handle": h, "name": real_name(h) if h else None,
                         "team": team, **a})
        rows.sort(key=lambda r: -r["moves"])
        activity[season] = rows

    # 88 rows, two per trade. Pair on (season, timestamp) and shout if that is ever
    # ambiguous - the same collision that merged three Sleeper-era-adjacent trades.
    pairs, collisions = defaultdict(list), []
    for season, when, team, players in (src.get("pre2014Trades") or []):
        pairs[(season, when)].append((team, players))
    pre = []
    for (season, when), sides in sorted(pairs.items(), key=lambda kv: kv[0][0]):
        if len(sides) != 2:
            collisions.append(f"{season} {when} has {len(sides)} sides")
            continue
        out_sides = []
        for team, players in sides:
            h = handle_for(season, team)
            if h is None:
                unresolved.append(f"trade {season} {team}")
            out_sides.append({"handle": h, "name": real_name(h) if h else None,
                              "team": team, "got": players})
        pre.append({"season": season, "when": when, "sides": out_sides})

    # FAB offers: the contested half of every waiver, 2014-2020. waivers.json has only
    # the winning pickups, so the losing bids were nowhere until yahoo_faab.py read them.
    faab = []
    fsrc = read_json(os.path.join(vault_manual, "_yahoo_faab_offers.json"), None) or {}
    for season, rows in sorted((fsrc.get("seasons") or {}).items()):
        for r in rows:
            losers = [{"handle": handle_for(int(season), l["team"]), "team": l["team"],
                       "bid": l["bid"], "why": l["why"]} for l in (r.get("losers") or [])]
            wh = handle_for(int(season), r.get("team") or "")
            faab.append({"season": int(season), "when": r.get("when", ""),
                         "player": r.get("player", ""), "bid": r.get("bid"),
                         "handle": wh, "name": real_name(wh) if wh else None,
                         "team": r.get("team", ""), "losers": losers})

    write_json(os.path.join(DATA, "yahoo_history.json"), {
        "activity": activity,
        "faab": faab,
        "settings": src.get("settings") or {},
        "buyIn": src.get("buyIn") or {},
        "commissioners": [dict(c, name=real_name(c.get("handle")))
                          for c in (src.get("commissioners") or [])],
        "pre2014Trades": pre,
        "note": src.get("source", ""),
    })
    msg = (f"{sum(len(v) for v in activity.values())} team-seasons of activity, "
           f"{sum(len(v) for v in (src.get('settings') or {}).values())} settings changes, "
           f"{len(pre)} pre-2014 trades, {len(faab)} contested waiver claims")
    if collisions:
        msg += " - PAIRING PROBLEM: " + "; ".join(collisions)
    if unresolved:
        msg += " - UNRESOLVED: " + ", ".join(unresolved[:6])
    return msg


def build_unclaimed(history):
    """unclaimed.json: the team-seasons whose manager was never identified.

    These are the handles history.json marks hidden - a leading '?' in the vault data.
    They are deliberately kept out of managers.json, because awards.py, record_watch.py,
    flpHistory.js and CombinedStandings.svelte all exclude hidden handles from awards,
    CAREER totals and the all-time rank, and putting a team-season in the managers list
    would undo that.

    Career only, on purpose. An unidentified team's games may belong to a manager who is
    already on those lists, so ranking it as a separate career invents a competitor and
    understates whoever really played those weeks. A SEASON record is different: one
    team-season stands on its own whoever held the remote, so hidden handles do compete
    for season records and currently hold three of them. Do not "fix" that to match the
    career rule - it is the intended split.

    Written for every repo, empty where there are none, so the page can import it.
    """
    mgrs = history.get("managers") or {}
    shown = lambda x: (mgrs.get(x) or {}).get("name") or x

    hidden_all = {h for h, m in mgrs.items() if m.get("hidden")}
    known = {h for h in mgrs if h not in hidden_all}        # people we can name

    # A manager who joined later cannot be an earlier team. Nothing in the data says so -
    # a hidden team is a privacy setting, not an absence - so this is hand-set in
    # manager_overrides.json, e.g. {"PapaMidnight": {"firstSeason": 2017}}.
    joined = {h: cfg["firstSeason"]
              for h, cfg in (read_json(os.path.join(DATA, "manager_overrides.json"), {}) or {}).items()
              if isinstance(cfg, dict) and isinstance(cfg.get("firstSeason"), int)}
    eligible = lambda h, season: joined.get(h, 0) <= season
    played_in = defaultdict(set)                            # season -> handles that season
    for g in history["games"]:
        played_in[g[0]].add(g[3]); played_in[g[0]].add(g[5])

    # first and last season each nameable manager is seen under his own name
    first_seen, last_seen = {}, {}
    for g in history["games"]:
        for who in (g[3], g[5]):
            if who in known:
                first_seen[who] = min(first_seen.get(who, 9999), g[0])
                last_seen[who] = max(last_seen.get(who, 0), g[0])

    def unaccounted(season):
        """Managers identified in an EARLIER and a LATER season who have no team of their
        own in this one. The best lead the data offers, but NOT proof: a manager can sit
        a season out and come back. Treat it as "worth asking him", not as a conclusion.
        The airtight part is the ruled-out list, which rests on one team per person per
        season."""
        return sorted((k for k in known
                       if k not in played_in[season]
                       and first_seen.get(k, 9999) < season < last_seen.get(k, 0)),
                      key=lambda x: real_name(x).lower())

    # Who played for these teams. Both files cover the Yahoo era and these handles, and
    # both are written by extras.build_all, which is why the call to this function sits
    # after extras in main(). Missing files just mean the sections are left out.
    pdata = read_json(os.path.join(STATIC, "players.json"), {}) or {}
    picks = (read_json(os.path.join(STATIC, "drafts.json"), {}) or {}).get("picks") or []

    teams = []
    for h in sorted(h for h, m in mgrs.items() if m.get("hidden")):
        w, l, titles, finals, seasons, vs = _career(h, history["games"])
        by_season, ties = [], 0
        for season in sorted(seasons):
            sw = sl = st = 0
            pf = pa = 0.0
            games = []
            for s, wk, _e, a, points_a, b, points_b, playoff, label in history["games"]:
                if s != season or h not in (a, b):
                    continue
                me, opp = (points_a, points_b) if a == h else (points_b, points_a)
                other = b if a == h else a
                pf += me; pa += opp
                if not playoff:
                    if me > opp: sw += 1
                    elif me < opp: sl += 1
                    else: st += 1
                games.append({"week": wk, "opponent": other, "opponentName": shown(other),
                              "score": round(me, 2), "opponentScore": round(opp, 2),
                              "result": "W" if me > opp else ("L" if me < opp else "T"),
                              "playoff": bool(playoff), "label": label})
            ties += st
            by_season.append({
                "season": season,
                "teamName": _team_name(history, season, h),
                "record": f"{sw}-{sl}" + (f"-{st}" if st else ""),
                "pointsFor": round(pf, 2), "pointsAgainst": round(pa, 2),
                # the consolation bracket carries playoff=True as well, so a real
                # playoff appearance means a game in one of the actual rounds
                "madePlayoffs": any(g["playoff"] and g["label"] in REAL_ROUNDS for g in games),
                "playoffResults": [g["label"] for g in games if g["playoff"] and g["label"]],
                "wonTitle": any(g["label"] == "Championship" and g["result"] == "W" for g in games),
                "lostFinal": any(g["label"] == "Championship" and g["result"] == "L" for g in games),
                "games": sorted(games, key=lambda g: g["week"]),
            })
        allg = [g for s in by_season for g in s["games"]]
        if not allg:
            continue

        # players.json rows are [season, handle, points, starts, weeks, bench]
        tally = {}
        for pl in (pdata.get("players") or []):
            got = [r for r in (pl.get("s") or []) if len(r) > 3 and r[1] == h]
            if not got:
                continue
            tally[pl["n"]] = {"name": pl["n"], "pos": pl.get("p"),
                              "points": round(sum(r[2] for r in got), 2),
                              "starts": sum(r[3] for r in got),
                              "seasons": sorted({r[0] for r in got})}
        top_players = sorted(tally.values(), key=lambda x: -x["points"])[:14]

        # drafts.json picks are [season, round, pick, manager, player, pos, ...]
        drafted = defaultdict(list)
        for r in picks:
            if len(r) > 5 and r[3] == h:
                drafted[r[0]].append({"round": r[1], "pick": r[2], "player": r[4], "pos": r[5]})
        draft = [{"season": s, "picks": sorted(v, key=lambda x: (x["round"], x["pick"]))}
                 for s, v in sorted(drafted.items())]
        best = max(allg, key=lambda g: g["score"])
        worst = min(allg, key=lambda g: g["score"])
        teams.append({
            "slug": _slug(h),
            "handle": h,
            "name": shown(h),
            "seasons": sorted(seasons),
            "record": f"{w}-{l}" + (f"-{ties}" if ties else ""),
            "gamesPlayed": len(allg),
            "pointsFor": round(sum(s["pointsFor"] for s in by_season), 2),
            "pointsAgainst": round(sum(s["pointsAgainst"] for s in by_season), 2),
            "titles": titles,
            "finalsLost": [s["season"] for s in by_season if s["lostFinal"]],
            "playoffSeasons": [s["season"] for s in by_season if s["madePlayoffs"]],
            "teamNames": sorted({s["teamName"] for s in by_season if s["teamName"]}),
            "bestWeek": best, "worstWeek": worst,
            "topPlayers": top_players,
            "draft": draft,
            "playedMost": [{"opponent": o, "name": shown(o), "w": wl[0], "l": wl[1]}
                           for o, wl in sorted(vs.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
                           if o != h][:8],
            "bySeason": by_season,
        })
    # --- who each team cannot be, and who is left ------------------------------------
    # A person holds one team per season, so anyone identified in a season is ruled out
    # for every unidentified team in it, and the other unidentified teams in that season
    # are certainly other people. A team listed in two seasons has to clear both.
    by_slug = {t["slug"]: t for t in teams}
    for t in teams:
        h, mine = t["handle"], set(t["seasons"])
        out_by_season, same_season = [], []
        for s in t["seasons"]:
            ident = sorted(played_in[s] & known, key=lambda x: real_name(x).lower())
            pool = {k for k in known if eligible(k, s)}
            others = sorted((played_in[s] & hidden_all) - {h}, key=lambda x: shown(x).lower())
            gap = [k for k in unaccounted(s) if eligible(k, s)]
            later = sorted((k for k in pool if first_seen.get(k, 9999) > s),
                           key=lambda x: real_name(x).lower())
            out_by_season.append({"season": s,
                                  "ruledOut": [real_name(x) for x in ident],
                                  "otherUnidentified": [shown(x) for x in others],
                                  "inLeagueUnaccounted": [real_name(x) for x in gap],
                                  "firstSeenLater": [{"name": real_name(x), "from": first_seen[x]}
                                                     for x in later]})
            same_season += others
        ruled = set()
        for s in t["seasons"]:
            ruled |= (played_in[s] & known)
        # known members with no team of their own in any of this team's seasons, who had
        # joined the league by then
        could = sorted({k for k in known - ruled if all(eligible(k, s) for s in t["seasons"])},
                       key=lambda x: real_name(x).lower())

        # Could another unidentified team be the same manager? Only one in a season this
        # team did not play, since two in the same season cannot be one person.
        maybe = []
        for other in teams:
            if other["handle"] == h or (set(other["seasons"]) & mine):
                continue
            mine_picks = {p["player"] for d in t["draft"] for p in d["picks"]}
            their_picks = {p["player"] for d in other["draft"] for p in d["picks"]}
            maybe.append({"slug": other["slug"], "name": other["name"],
                          "seasons": other["seasons"],
                          "sharedDraftPicks": sorted(mine_picks & their_picks)})
        maybe.sort(key=lambda m: (-len(m["sharedDraftPicks"]), m["name"]))

        # someone unaccounted for in every one of this team's seasons is the best lead
        strong = (set.intersection(*[{k for k in unaccounted(s) if eligible(k, s)}
                                     for s in t["seasons"]]) if t["seasons"] else set())
        t["strongCandidates"] = [real_name(x) for x in
                                 sorted(strong, key=lambda x: real_name(x).lower())]
        t["bySeasonSuspects"] = out_by_season
        t["ruledOut"] = [real_name(x) for x in sorted(ruled, key=lambda x: real_name(x).lower())]
        t["couldBe"] = [real_name(x) for x in could]
        t["certainlyNot"] = sorted({shown(x) for x in same_season})
        t["maybeSameManager"] = maybe

    slugs = [t["slug"] for t in teams]
    for t in teams:                      # a duplicate slug would make two pages collide
        if slugs.count(t["slug"]) > 1:
            t["slug"] = _slug(t["handle"] + "-" + str(t["seasons"][0]))
    write_json(os.path.join(DATA, "unclaimed.json"), teams)
    return teams


# ---------------------------------------------------------------- main
ROLLED = False      # set when this run moved the site to a new season


def find_renewed(league_id, new_season):
    """The league Sleeper renewed this one into for new_season, or None."""
    for u in get(f"https://api.sleeper.app/v1/league/{league_id}/users") or []:
        for lg in get(f"https://api.sleeper.app/v1/user/{u['user_id']}/leagues/nfl/{new_season}") or []:
            if str(lg.get("previous_league_id")) == str(league_id):
                return lg
    return None


def rollover(state):
    """Season rollover without a hand edit (2026-11-15).

    site_config.json carries the league id and season, and they used to be typed
    in every August. Now: once Sleeper's regular season is a later year than the
    one in the config, look for the league this one was renewed into. When it has
    drafted and is in season, write the new id and season into site_config.json
    and src/lib/utils/leagueInfo.js (the pages read the id from there) and carry
    on with them. A vault site (FL Players) is only told, because the season
    that just ended has to be in the vault first or it would drop out of history.
    Any failure leaves the config alone."""
    global LEAGUE_ID, SEASON, ROLLED
    try:
        if CONFIG.get("shim") or state.get("season_type") != "regular":
            return
        while int(state.get("season") or 0) > SEASON:
            nxt = find_renewed(LEAGUE_ID, SEASON + 1)
            if not nxt:
                print(f"ROLLOVER: Sleeper is on {state.get('season')} but no league was renewed from {LEAGUE_ID}; staying on {SEASON}")
                return
            if nxt.get("status") != "in_season":
                print(f"ROLLOVER: the {SEASON + 1} league exists ({nxt.get('status')}) but is not in season yet; staying on {SEASON}")
                return
            if HISTORY_SOURCE == "vault":
                print(f"ROLLOVER NEEDED: the {SEASON + 1} league is {nxt['league_id']}. Put {SEASON} in the vault, then set "
                      f"league_id and season in scripts/site_config.json and leagueID in src/lib/utils/leagueInfo.js")
                return
            old = str(LEAGUE_ID)
            CONFIG["league_id"] = str(nxt["league_id"]); CONFIG["season"] = SEASON + 1
            write_json(os.path.join(REPO, "scripts", "site_config.json"), CONFIG)
            li = os.path.join(REPO, "src", "lib", "utils", "leagueInfo.js")
            txt = open(li, encoding="utf-8").read()
            if old in txt:
                with open(li, "w", encoding="utf-8", newline="") as f:
                    f.write(txt.replace(old, str(nxt["league_id"])))
            LEAGUE_ID = CONFIG["league_id"]; SEASON = int(CONFIG["season"]); ROLLED = True
            print(f"ROLLOVER: now on {SEASON}, league {LEAGUE_ID}")
    except Exception as e:
        print("rollover check failed, config left alone:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, help="rebuild just this week's recap")
    ap.add_argument("--all", action="store_true", help="rebuild every finished week")
    ap.add_argument("--push", action="store_true", help="git commit and push")
    args = ap.parse_args()

    if CONFIG.get("shim"):            # rebuild the ESPN copies first
        import espn_shim             # only exists in a shimmed repo
        espn_shim.main()

    state = sleeper("/state/nfl")
    rollover(state)
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
           "odds_prior": CONFIG.get("odds_prior"), "hof": CONFIG.get("hof"),   # "current" (redraft default) or "last_season"
           "data": DATA, "static": STATIC, "vault_manual": VAULT_MANUAL,
           "write_json": write_json, "read_json": read_json, "sleeper": sleeper,
           # the name to print where a line of built text names a manager
           "shown": ((lambda h: SHOWN.get(h, (h,))[0]) if CONFIG.get("names") == "handles"
                     else (lambda h: h))}
    # BEFORE extras, because the tracker cards are built inside extras.build_all and
    # read these two files. Written after it, a fresh clone's first build would produce
    # empty Yahoo cards and only the second build would fill them.
    # FL Players only: this is that league's Yahoo history, and the other repos share
    # the vault path without sharing the team names, so an ungated run would write a
    # file of nulls for them.
    if HISTORY_SOURCE == "vault":
        print("vetoed_trades.json:", build_vetoed(history, VAULT_MANUAL))
        print("yahoo_history.json:", build_yahoo_history(history, VAULT_MANUAL))
    print("extras:", extras.build_all(ctx))
    # after extras, which writes the players and draft files unclaimed.json quotes
    print(f"unclaimed.json: {len(build_unclaimed(history))} unidentified teams")
    # Across the Leagues (2026-10-14): reads the other Sleeper repos' history.json
    try:
        import crossleague
        print("crossleague:", crossleague.build(REPO, DATA, write_json))
    except Exception as e:
        print("crossleague failed:", e)

    if BAD_LINEUPS:
        print(f"STOPPED: {len(BAD_LINEUPS)} team-weeks have a best lineup below the real score:")
        for line in BAD_LINEUPS[:10]:
            print("  " + line)
        raise SystemExit("fix the player positions before pushing (see BAD_LINEUPS in update_site.py)")

    if args.push:
        paths = ["src/lib/data", "static/data"]
        if ROLLED:                    # the new league id has to reach the live pages too
            paths += ["scripts/site_config.json", "src/lib/utils/leagueInfo.js"]
        if CONFIG.get("shim"):        # the ESPN copies the pages read in the browser
            paths.append("static/shim")
        subprocess.run(["git", "-C", REPO, "add", *paths], check=True)
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
