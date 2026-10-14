"""nfl_news.py - the week's real NFL headlines, tied to this league.

Writes src/lib/data/nfl_news.json at the Tuesday update. Source: ESPN's public
NFL news feed, one call per NFL team (the league-wide feed only reaches back
about half a day; team feeds reach back two weeks). Shared across repos through
a cache in ~/.cache, so five league updates in a row fetch once.

Each headline keeps ESPN's headline, date and link (never the article text),
the league players it names and who owns them, and the ripple: every other
rostered QB, RB, WR and TE on that NFL offense, by owner. A QB benching is news
for his receivers' owners too.

Headlines are what ESPN reported on the date shown. Injury and depth-chart
items can change before kickoff, so the page says when it was read.
"""
import os
import re
import json
import time
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone

TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?team={abbr}&limit=50"
ESPN_TO_SLEEPER = {"WSH": "WAS"}
OFFENSE = ("QB", "RB", "WR", "TE")
DAYS = 7
CACHE_HOURS = 6
# a team-only headline (no player named) has to be about football to count
IMPACT = re.compile(r"\b(qb|quarterback|start(s|er|ing)?|bench(ed|ing)?|backup|coach|coordinator|play-?call\w*|"
                    r"fired|injur\w*|out|ir|reserve|sprain|torn|fracture|concussion|surgery|trade[ds]?|sign(s|ed)?|"
                    r"release[ds]?|waive[ds]?|suspend\w*|return\w*|activat\w*|depth|role|snaps?|targets?|carries)\b", re.I)
SKIP_TYPES = {"Media"}
# game-status items ("questionable vs. X", "will play") are stale once that game is played
STATUS = re.compile(r"questionable|doubtful|ruled out|will play|to play (sunday|monday|thursday|saturday)|"
                    r"expect\w* .*to play|game-time|unlikely vs|"
                    r"\bout (vs|against)\b|\bout;|to start (snf|mnf|tnf|sunday|monday|thursday)|inactive", re.I)
# fantasy advice columns are not NFL storylines; the league makes its own calls
ADVICE = re.compile(r"fantasy|rankings|pickups|waiver|start 'em|sit 'em|knockout|sleepers|busts|dfs|betting|odds|"
                    r"mock draft|draft order|power rankings|arrivals|xfp|quotes|overreactions|takeaways|"
                    r"things (we|i) (learned|think)|winners and losers|grades", re.I)
# off-field stories: not what moves a lineup
OFF_FIELD = re.compile(r"\b(dies|died|death|trial|lawsuit|verdict|podcast|owners?|trailer|hulu|netflix|charity|"
                       r"wedding|fashion|memo|documentary|hall of fame)\b", re.I)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 league-page-updater"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"[^a-z]+", " ", s).strip()


def fetch_all():
    """Every NFL team's recent headlines, de-duplicated. Cached for a few hours."""
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "league_page_projections")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "espn_nfl_news.json")
    try:
        if time.time() - os.path.getmtime(path) < CACHE_HOURS * 3600:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except OSError:
        pass
    teams = _get(TEAMS_URL)["sports"][0]["leagues"][0]["teams"]
    id_abbr = {t["team"]["id"]: ESPN_TO_SLEEPER.get(t["team"]["abbreviation"], t["team"]["abbreviation"]) for t in teams}
    seen, out = set(), []
    for t in teams:
        abbr = t["team"]["abbreviation"].lower()
        try:
            arts = _get(NEWS_URL.format(abbr=abbr)).get("articles") or []
        except Exception as e:
            print("nfl_news: feed failed for", abbr, e)
            continue
        for a in arts:
            key = a.get("id") or (a.get("links") or {}).get("web", {}).get("href") or a.get("headline")
            if not key or key in seen:
                continue
            seen.add(key)
            cats = a.get("categories") or []
            out.append({
                "id": str(key),
                "type": a.get("type") or "",
                "headline": a.get("headline") or "",
                "published": a.get("published") or "",
                "url": (a.get("links") or {}).get("web", {}).get("href"),
                "athletes": [c.get("description") for c in cats if c.get("type") == "athlete" and c.get("description")],
                "teams": sorted({id_abbr.get(str(c.get("teamId") or (c.get("team") or {}).get("id")))
                                 for c in cats if c.get("type") == "team"} - {None}),
            })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def build_nfl_news(ctx, limit=14):
    S = ctx["cur"]
    arts = fetch_all()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=DAYS)
    # this league's rostered players, by name and by NFL team
    owner, by_name, by_team = {}, {}, {}
    for r in S.rosters:
        h = S.handle.get(r["roster_id"])
        if not h:
            continue
        for pid in r.get("players") or []:
            info = S.pinfo(pid)
            if info["pos"] not in OFFENSE and info["pos"] not in ("K", "DEF"):
                continue
            owner[pid] = h
            by_name.setdefault(norm(info["name"]), []).append(pid)
            if info["pos"] in OFFENSE and info.get("team"):
                by_team.setdefault(info["team"], []).append(pid)
    items = []
    for a in arts:
        if (a["type"] in SKIP_TYPES or not a["published"] or ADVICE.search(a["headline"])
                or OFF_FIELD.search(a["headline"])):
            continue
        try:
            when = datetime.fromisoformat(a["published"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if when < cutoff:
            continue
        if STATUS.search(a["headline"]) and now - when > timedelta(days=3):
            continue
        named = [pid for n in a["athletes"] for pid in by_name.get(norm(n), [])]
        hl = norm(a["headline"])
        # a player the headline is about, not one ESPN merely tagged
        in_hl = [p for p in named if norm(S.pinfo(p)["name"]).split()[-1] in hl.split()]
        nfl_teams = set(a["teams"]) | {S.pinfo(p).get("team") for p in named if S.pinfo(p).get("team")}
        if not named and not (a["type"] == "HeadlineNews" and nfl_teams and IMPACT.search(a["headline"])):
            continue
        named_teams = {S.pinfo(p).get("team") for p in named}
        if a["type"] != "HeadlineNews" and len(named_teams) > 2:
            continue                       # a league-wide roundup, not one team's story
        # the ripple only makes sense when the story is about one or two offenses
        # ripple from the offenses the headline is about (a rival quoted in it is not news for his team)
        hl_teams = {S.pinfo(p).get("team") for p in in_hl} - {None}
        rteams = hl_teams or nfl_teams
        if named and all(S.pinfo(p)["pos"] in ("K", "DEF") for p in named):
            rteams = set()                 # a kicker's job is not news for the offense
        ripple = ([p for t in sorted(rteams) for p in by_team.get(t, []) if p not in named]
                  if len(rteams) <= 2 else [])
        if not named and not ripple:
            continue
        def row(pid):
            i = S.pinfo(pid)
            return {"n": i["name"], "p": i["pos"], "t": i.get("team") or "", "h": owner[pid]}
        managers = sorted({owner[p] for p in named + ripple})
        items.append({
            "headline": a["headline"], "url": a["url"], "date": a["published"][:10],
            "kind": "news" if a["type"] == "HeadlineNews" else "story",
            "teams": sorted(nfl_teams - {None}),
            "named": [row(p) for p in in_hl + [q for q in named if q not in in_hl]],
            "lead": [S.pinfo(p)["name"] for p in in_hl],
            "ripple": [row(p) for p in ripple],
            "managers": managers,
            "score": 4 * len(in_hl) + 1 * (len(named) - len(in_hl)) + 0.5 * min(len(ripple), 8) + (3 if a["type"] == "HeadlineNews" else 0)
                     + (2 if IMPACT.search(a["headline"]) else 0)
                     + (3 if now - when < timedelta(days=2) else 1 if now - when < timedelta(days=4) else 0),
            "_key": tuple(sorted(in_hl)) or tuple(sorted(named)) or tuple(sorted(nfl_teams)),
            "_teams": (a["published"][:10], tuple(sorted(nfl_teams - {None}))),
        })
    # strongest league impact first, newest first among ties
    items.sort(key=lambda x: x["date"], reverse=True)
    items.sort(key=lambda x: -x["score"])
    # one headline per storyline: the same players (or the same teams) only once
    top, seen = [], set()
    for x in items:
        k, kt = x.pop("_key"), x.pop("_teams")
        if k in seen or (len(kt[1]) == 2 and kt in seen):   # same game written up twice
            continue
        seen.add(k)
        seen.add(kt)
        top.append(x)
        if len(top) >= limit:
            break
    doc = {"read_at": now.isoformat(timespec="minutes"), "days": DAYS, "count": len(items), "items": top,
           "source": "ESPN NFL news, headlines and links only",
           "note": "Headlines as ESPN reported them on the date shown. Injury and depth-chart news can change before kickoff."}
    ctx["write_json"](os.path.join(ctx["data"], "nfl_news.json"), doc)
    return doc
