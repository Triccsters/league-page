"""Across the leagues: the same people meet in more than one of T.J.'s Sleeper leagues.

Reads history.json from the four Sleeper league repos next to this one and writes
src/lib/data/crossleague.json for the /across page. League Bound is left out: it is
on ESPN and its history only has team names, so nobody there can be matched.

Matching: a person is a Sleeper account. update_site.py already folds old display
names into the current one (CANON: Austin7Rock -> RockMNwild, Tongueohvaeloa ->
TuanonStan), so the same handle in two leagues is the same account. Two accounts
owned by one person would not be matched; PEOPLE below is where to join them.

Called from update_site.py after the extras. Each league's own daily run rewrites
its copy, so a copy can be up to a day behind the other leagues.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

LEAGUES = [  # repo, name, site
    ("league-page", "FL Players", "https://league-page-tan-six.vercel.app"),
    ("league-fl-evolution", "FL Evolution", "https://league-fl-evolution.vercel.app"),
    ("league-lets-go-brandon", "Lets go Brandon", "https://league-lets-go-brandon.vercel.app"),
    ("league-megalabowl", "Megalabowl", "https://league-megalabowl.vercel.app"),
]

# Extra handle -> person joins for one person on two Sleeper accounts. Empty: none
# known as of 2026-10-14.
PEOPLE = {}


def build(repo, data_dir, write_json):
    me = os.path.basename(repo)
    out_path = os.path.join(data_dir, "crossleague.json")
    if me not in {r for r, _n, _s in LEAGUES}:
        write_json(out_path, {"generated": None, "skipped": "not a Sleeper league"})
        return "skipped"
    root = os.path.dirname(repo)
    leagues, hist = [], {}
    for i, (r, name, site) in enumerate(LEAGUES):
        p = os.path.join(root, r, "src", "lib", "data", "history.json")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            hist[i] = json.load(f)
        seasons = sorted({g[0] for g in hist[i]["games"]})
        leagues.append({"i": i, "name": name, "site": site, "first": seasons[0], "last": seasons[-1],
                        "current": hist[i].get("current", [])})

    person = lambda h: PEOPLE.get(h, h)
    # first names come from FL Players, the only league that keeps them
    names = {}
    for i, h in hist.items():
        for hd, m in h["managers"].items():
            if not m.get("hidden") and m.get("name") and m["name"] != hd:
                names.setdefault(person(hd), m["name"])

    where = defaultdict(set)
    for i, h in hist.items():
        for g in h["games"]:
            where[person(g[3])].add(i)
            where[person(g[5])].add(i)
    multi = sorted(p for p, s in where.items() if len(s) > 1)
    multi_set = set(multi)

    # every game among people who play in 2+ leagues, from the lower-sorted person's side
    pairs = defaultdict(list)
    records = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))   # person -> league -> w,l,t (regular season)
    for i, h in hist.items():
        for s, w, _e, a, pa, b, pb, playoff, label in h["games"]:
            a, b = person(a), person(b)
            for me_, mp, op in ((a, pa, pb), (b, pb, pa)):
                if me_ in multi_set and not playoff:
                    r = records[me_][i]
                    r[0 if mp > op else 1 if mp < op else 2] += 1
            if a in multi_set and b in multi_set and a != b:
                x, y = sorted((a, b))
                xp, yp = (pa, pb) if a == x else (pb, pa)
                pairs[(x, y)].append([s, w, i, round(xp, 2), round(yp, 2), 1 if playoff else 0, label or ""])

    pair_rows = []
    for (x, y), gl in pairs.items():
        gl.sort(key=lambda g: (g[0], g[1], g[2]))
        in_leagues = sorted({g[2] for g in gl})
        pair_rows.append({"x": x, "y": y, "leagues": in_leagues, "games": gl})
    pair_rows.sort(key=lambda r: (-len(r["leagues"]), -len(r["games"]), r["x"], r["y"]))

    people = [{"h": p, "name": names.get(p), "leagues": sorted(where[p]),
               "record": {str(i): v for i, v in sorted(records[p].items())}} for p in multi]
    out = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "leagues": leagues, "people": people, "pairs": pair_rows,
           "note": "Same Sleeper account = same person. FL Players counts back to 2008, Yahoo years included."}
    write_json(out_path, out)
    return f"{len(people)} people in 2+ leagues, {sum(1 for r in pair_rows if len(r['leagues']) > 1)} pairs met in 2+"


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = os.path.join(repo, "src", "lib", "data")

    def wj(p, d):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print(build(repo, data, wj))
