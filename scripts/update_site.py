"""
update_site.py - weekly data refresh for the FL Players league page.

Writes static JSON the site reads (src/lib/data/):
  history.json          every game 2014 to now, both eras, canonical managers
  recaps/2026-wNN.json  one recap per completed week (your intro/video are kept)
  recaps/index.json     list of recaps, newest first

Usage, from the repo root on tricclt:
  python scripts/update_site.py            refresh history + any new recaps
  python scripts/update_site.py --week 3   rebuild one week's recap
  python scripts/update_site.py --push     also git commit + push (Vercel redeploys)

Yahoo 2014-2020 and Sleeper 2021-2025 come from the vault data layer (flp.py).
The current season is read live from api.sleeper.app.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "src", "lib", "data")
RECAPS = os.path.join(DATA, "recaps")
VAULT_MANUAL = os.environ.get(
    "FLP_MANUAL", r"C:\Users\trick\Documents\Fantasy Football Vault\_manual")

LEAGUE_ID = "1363926598088146944"   # FL Players 2026
SEASON = 2026
CANON = {"Austin7Rock": "RockMNwild", "Tongueohvaeloa": "TuanonStan"}

# Real names, confirmed by T.J. 2026-09-08. Second value is the Yahoo name.
MANAGERS = {
    "triccster": ("T.J.", "T.J.R"), "brettmn13": ("Brett", "Brett"),
    "Wallner": ("John Wallner", "John Wall"), "Colt45Johnson": ("Colt", "Colt"),
    "RockMNwild": ("Austin", "Austin"), "snelson91": ("Scott", "Scott"),
    "TuanonStan": ("James", "LordPmp"), "Jbird531": ("Joey", "Joey"),
    "YoungBuck04": ("Zak", "zak"), "butterygoop": ("Anthony", "Anthony"),
    "PapaMidnight": ("Mikey", "Mikey"), "thecreamer": ("Zach Nase", "zach"),
    "J Rock": ("J Rock", "J Rock"), "Tyler": ("Tyler", "Tyler"),
}

ELIG = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"}, "K": {"K"},
        "DEF": {"DEF"}, "FLEX": {"RB", "WR", "TE"},
        "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
SLOTS = ["Wed", "Thu", "Sun early", "Sun late", "SNF", "MNF"]
ESPN_ABBR = {"WSH": "WAS"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "flp-league-page"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def sleeper(path):
    return get("https://api.sleeper.app/v1" + path)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- season data
class Season:
    """Everything needed from Sleeper for the current season, fetched once."""

    def __init__(self):
        self.state = sleeper("/state/nfl")
        self.league = sleeper(f"/league/{LEAGUE_ID}")
        users = sleeper(f"/league/{LEAGUE_ID}/users")
        self.rosters = sleeper(f"/league/{LEAGUE_ID}/rosters")
        uname = {u["user_id"]: CANON.get(u["display_name"], u["display_name"])
                 for u in users}
        self.team_name = {u["user_id"]: (u.get("metadata") or {}).get("team_name")
                          for u in users}
        self.owner = {r["roster_id"]: r["owner_id"] for r in self.rosters}
        self.handle = {rid: uname.get(oid, f"Roster {rid}")
                       for rid, oid in self.owner.items()}
        self.slots = [s for s in self.league["roster_positions"] if s in ELIG]
        self.playoff_start = (self.league.get("settings") or {}).get(
            "playoff_week_start") or 15
        self._players = None
        self._matchups = {}

    @property
    def completed_weeks(self):
        """Weeks whose Monday game is over: everything before the current week."""
        if str(self.state.get("season")) != str(SEASON):
            return list(range(1, 18)) if self.league.get("status") == "complete" else []
        cur = self.state.get("display_week") or self.state.get("week") or 1
        if self.state.get("season_type") != "regular":
            cur = 19
        weeks = list(range(1, min(cur, 18)))
        # Sleeper may not have advanced its week yet on Tuesday morning; if every
        # game of its current week is final on ESPN, that week is done too.
        if cur <= 18 and cur not in weeks and week_is_final(cur):
            weeks.append(cur)
        return weeks

    def matchups(self, week):
        if week not in self._matchups:
            self._matchups[week] = sleeper(f"/league/{LEAGUE_ID}/matchups/{week}")
        return self._matchups[week]

    @property
    def players(self):
        if self._players is None:
            cache = os.path.join(VAULT_MANUAL, "players_nfl.json")
            age = None
            if os.path.exists(cache):
                age = datetime.now().timestamp() - os.path.getmtime(cache)
            if age is None or age > 3 * 86400:
                self._players = sleeper("/players/nfl")
                try:
                    with open(cache, "w", encoding="utf-8") as f:
                        json.dump(self._players, f)
                except OSError:
                    pass
            else:
                with open(cache, encoding="utf-8") as f:
                    self._players = json.load(f)
        return self._players

    def pinfo(self, pid):
        p = self.players.get(pid) or {}
        if not p and not pid.isdigit():          # team defence, id is the team
            return {"name": f"{pid} DEF", "pos": "DEF", "team": pid}
        name = p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        return {"name": name or pid, "pos": p.get("position") or "?",
                "team": p.get("team")}

    def pairs(self, week):
        by = defaultdict(list)
        for m in self.matchups(week):
            if m.get("matchup_id") is not None:
                by[m["matchup_id"]].append(m)
        return [v for v in by.values() if len(v) == 2]


# ---------------------------------------------------------------- history
def build_history(season):
    sys.path.insert(0, VAULT_MANUAL)
    import flp  # noqa: E402  (vault data layer)

    games = []
    for g in flp.games():
        if g.season >= SEASON:
            continue
        games.append([g.season, g.week, g.era, g.a, round(g.pa, 2),
                      g.b, round(g.pb, 2), bool(g.playoff), g.label])
    for wk in season.completed_weeks:
        playoff = wk >= season.playoff_start
        for a, b in season.pairs(wk):
            games.append([SEASON, wk, "sleeper", season.handle[a["roster_id"]],
                          round(a.get("points") or 0, 2),
                          season.handle[b["roster_id"]],
                          round(b.get("points") or 0, 2), playoff, None])
    games.sort(key=lambda g: (g[0], g[1]))
    managers = {h: {"name": n, "yahoo": y} for h, (n, y) in MANAGERS.items()}
    current = sorted(set(season.handle.values()))
    out = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fields": ["season", "week", "era", "a", "pa", "b", "pb", "playoff", "label"],
        "managers": managers,
        "current": current,
        "games": games,
    }
    write_json(os.path.join(DATA, "history.json"), out)
    return out


# ---------------------------------------------------------------- recap
def week_is_final(week):
    try:
        sb = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
                 f"scoreboard?week={week}&seasontype=2&dates={SEASON}")
    except Exception:
        return False
    evs = sb.get("events", [])
    return bool(evs) and all(ev["status"]["type"].get("completed") for ev in evs)


def kickoff_slots(week):
    """Team abbreviation -> Wed/Thu/Sun early/Sun late/SNF/MNF from ESPN."""
    sb = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
             f"scoreboard?week={week}&seasontype=2&dates={SEASON}")
    out = {}
    for ev in sb.get("events", []):
        # ESPN dates are UTC; shift to US Central to name the window.
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


def side(season, m, slot_of):
    pts = round(m.get("points") or 0, 2)
    pp = m.get("players_points") or {}
    starters = [p for p in (m.get("starters") or []) if p and p != "0"]
    run = {s: 0.0 for s in SLOTS}
    for p, v in zip(m.get("starters") or [], m.get("starters_points") or []):
        if not p or p == "0":
            continue
        s = slot_of.get(season.pinfo(p)["team"])
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
            if mp > op:
                r[0] += 1
            elif mp < op:
                r[1] += 1
            else:
                r[2] += 1
    rows = [{"manager": m, "w": r[0], "l": r[1], "t": r[2], "pf": round(r[3], 2)}
            for m, r in rec.items()]
    rows.sort(key=lambda x: (-x["w"], -x["pf"]))
    return rows


def h2h_line(history, a, b, before):
    """All-time record between a and b, both eras, before this season-week."""
    wa = wb = 0
    for s, w, _e, x, px, y, py, _p, _l in history["games"]:
        if (s, w) >= before or {x, y} != {a, b}:
            continue
        winner = x if px > py else y if py > px else None
        wa += winner == a
        wb += winner == b
    return [wa, wb]


def build_recap(season, history, week):
    path = os.path.join(RECAPS, f"{SEASON}-w{week:02d}.json")
    old = read_json(path, {}) or {}
    slot_of = kickoff_slots(week)
    games = []
    for a, b in season.pairs(week):
        sa, sb = side(season, a, slot_of), side(season, b, slot_of)
        if sb["points"] > sa["points"]:
            sa, sb = sb, sa
        games.append({"winner": sa, "loser": sb,
                      "margin": round(sa["points"] - sb["points"], 2),
                      "h2h_before": h2h_line(history, sa["manager"], sb["manager"],
                                             (SEASON, week))})
    games.sort(key=lambda g: g["margin"])
    everyone = [s for g in games for s in (g["winner"], g["loser"])]
    top_player = max(({"manager": s["manager"], **t} for s in everyone for t in s["top"]),
                     key=lambda x: x["pts"], default=None)
    regret = max(everyone, key=lambda s: s["left_on_bench"], default=None)
    high = max(everyone, key=lambda s: s["points"], default=None)
    low = min(everyone, key=lambda s: s["points"], default=None)
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
        c = (r.get("facts") or {}).get("closest") or {}
        items.append({"slug": r["slug"], "season": r["season"], "week": r["week"],
                      "title": r["title"], "intro": r.get("intro", "")[:240],
                      "video": bool(r.get("video")),
                      "closest": c and f'{c["winner"]["manager"]} over {c["loser"]["manager"]} by {c["margin"]}'})
    write_json(os.path.join(RECAPS, "index.json"), items)
    return items


# ---------------------------------------------------------------- managers
def build_managers(season, history):
    """src/lib/data/managers.json for the template's Managers pages.

    Anything in src/lib/data/manager_overrides.json (keyed by Sleeper handle)
    replaces the generated value, so hand-written bios and photos survive.
    """
    overrides = read_json(os.path.join(DATA, "manager_overrides.json"), {}) or {}
    users = sleeper(f"/league/{LEAGUE_ID}/users")
    handle_of = {u["user_id"]: CANON.get(u["display_name"], u["display_name"])
                 for u in users}
    order = sorted(users, key=lambda u: MANAGERS.get(handle_of[u["user_id"]], (u["display_name"],))[0])
    index = {handle_of[u["user_id"]]: i for i, u in enumerate(order)}

    REAL = {"Quarterfinal", "Semifinal", "Championship"}
    out = []
    for u in order:
        h = handle_of[u["user_id"]]
        name = MANAGERS.get(h, (h,))[0]
        w = l = 0
        titles, finals, seasons = [], 0, set()
        vs = defaultdict(lambda: [0, 0])
        for s, wk, _e, a, pa, b, pb, playoff, label in history["games"]:
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
            if not playoff or label in REAL:
                vs[other][0 if me > opp else 1] += 1
        current_foes = [o for o in vs if o in index]
        nemesis = max(current_foes, key=lambda o: (vs[o][1] - vs[o][0], vs[o][1]), default=None)
        bits = [f"Regular season since {min(seasons)}: {w}-{l}."]
        if titles:
            bits.append(f"Champion: {', '.join(map(str, titles))}.")
        elif finals:
            bits.append(f"{finals} final{'s' if finals > 1 else ''}, still chasing a title.")
        else:
            bits.append("Still chasing a first title.")
        if nemesis:
            nw, nl = vs[nemesis]
            bits.append(f"Toughest opponent: {MANAGERS.get(nemesis, (nemesis,))[0]} ({nw}-{nl}).")
        slug = lambda x, y: "--".join(sorted([x, y]))
        bio = " ".join(bits)
        if nemesis:
            bio += f' <a href="/rivalries/{slug(h, nemesis)}">That rivalry</a> ·'
        bio += f' <a href="/rivalries?who={h}">All of {name}\'s rivalries</a>'
        entry = {
            "managerID": u["user_id"],
            "name": name,
            "photo": f"https://sleepercdn.com/avatars/{u['avatar']}" if u.get("avatar") else "/managers/question.jpg",
            "fantasyStart": min(seasons) if seasons else None,
            "bio": bio,
            "rival": {
                "name": MANAGERS.get(nemesis, (nemesis,))[0] if nemesis else "Everyone",
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
    ap.add_argument("--all", action="store_true", help="rebuild every completed week")
    ap.add_argument("--push", action="store_true", help="git commit and push")
    args = ap.parse_args()

    season = Season()
    history = build_history(season)
    print(f"history.json: {len(history['games'])} games "
          f"({sum(1 for g in history['games'] if g[0] == SEASON)} from {SEASON})")

    done = season.completed_weeks
    if args.week:
        weeks = [args.week]
    elif args.all:
        weeks = done
    else:   # weeks without a recap yet, plus the latest (scores can be corrected)
        weeks = [w for w in done
                 if not os.path.exists(os.path.join(RECAPS, f"{SEASON}-w{w:02d}.json"))]
        if done and done[-1] not in weeks:
            weeks.append(done[-1])
    for w in weeks:
        r = build_recap(season, history, w)
        print(f"recap week {w}: {len(r['games'])} games")
    build_index()
    print(f"managers.json: {len(build_managers(season, history))} managers")

    if args.push:
        subprocess.run(["git", "-C", REPO, "add", "src/lib/data"], check=True)
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
