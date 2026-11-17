"""grenades.json: players who bounced between rosters and kept landing in losses.

A "grenade", in the fantasy sense T.J. means: a guy who gets dropped and picked up
over and over, and whoever starts him seems to lose that week.

Three things have to be true at once, and the first run showed why all three are
needed:

  bounce   rostered by several managers, and handed off mid-season. Without this
           every bad player qualifies.
  return   points per start well under what that POSITION returns. Raw points
           per start makes every tight end look cursed - the TE median is 6.74
           against the RB median of 10.44 - so the comparison is positional.
  damage   his starts came in losses more often than chance. The base rate is
           about 50%, so a small sample is shrunk toward 50% rather than taken
           at face value: a 2-start player who lost twice is not a grenade.

Defences and kickers are ranked separately and never in the main list. Everyone
streams them - Ravens DEF has had 16 owners and 23 in-season handoffs - so they
would otherwise fill every slot and mean nothing.

Nothing here claims a player CAUSED a loss. It says he moved around a lot, he
returned less than his position does, and the lineups he was in lost. The page
says exactly that.
"""
import os
from collections import defaultdict

STREAMED = ("DEF", "K")       # ranked apart: everyone streams these
MIN_STARTS = 8                # below this a rate is noise
MIN_OWNERS = 3                # "bounces around" needs at least three homes
SHRINK = 10.0                 # pseudo-games pulling the loss rate toward the base
TOP = 60


def _r(x, d=2):
    return round(x + 0.0, d)


def build_grenades(ctx, rows):
    """rows: (season, week, h, k, name, pos, started, pts) - the same feed
    build_costly takes, so this sees every start in every season on record."""
    games = ctx["history"]["games"]

    # ---- who won each (season, week, manager) ------------------------
    result = {}
    for season, week, _era, a, pa, b, pb, _po, _lab in games:
        if pa is None or pb is None or not (pa or pb):
            continue
        if pa == pb:
            result[(season, week, a)] = result[(season, week, b)] = 0
        else:
            win, lose = (a, b) if pa > pb else (b, a)
            result[(season, week, win)] = 1
            result[(season, week, lose)] = -1

    # ---- per player: starts, points, owners, handoffs ----------------
    P = defaultdict(lambda: dict(name=None, pos=None, starts=0, pts=0.0,
                                 rostered=0, owners=set(), seasons=set(),
                                 won=0, lost=0, tied=0, byseason=defaultdict(set),
                                 worst=None))
    for season, week, h, k, name, pos, started, pts in rows:
        p = P[k]
        p["name"] = p["name"] or name
        p["pos"] = p["pos"] or pos
        p["rostered"] += 1
        p["owners"].add(h)
        p["seasons"].add(season)
        p["byseason"][season].add(h)
        if not started:
            continue
        p["starts"] += 1
        p["pts"] += pts or 0
        r = result.get((season, week, h))
        if r == 1:
            p["won"] += 1
        elif r == -1:
            p["lost"] += 1
            if p["worst"] is None or (pts or 0) < p["worst"]["pts"]:
                p["worst"] = dict(season=season, week=week, h=h, pts=_r(pts or 0))
        elif r == 0:
            p["tied"] += 1

    # ---- what a start is normally worth, by position -----------------
    pos_pts = defaultdict(list)
    for k, p in P.items():
        if p["starts"] >= MIN_STARTS:
            pos_pts[p["pos"]].append(p["pts"] / p["starts"])
    pos_median = {}
    for pos, vals in pos_pts.items():
        vals.sort()
        pos_median[pos] = vals[len(vals) // 2] if vals else 0.0

    # the base rate: how often a start lands in a win at all
    tw = sum(p["won"] for p in P.values())
    tl = sum(p["lost"] for p in P.values())
    base_loss = tl / (tw + tl) if (tw + tl) else 0.5

    out, streamed = [], []
    for k, p in P.items():
        decided = p["won"] + p["lost"]
        if p["starts"] < MIN_STARTS or decided < MIN_STARTS:
            continue
        owners = len(p["owners"])
        handoffs = sum(len(v) - 1 for v in p["byseason"].values())   # mid-season moves
        pps = p["pts"] / p["starts"]
        med = pos_median.get(p["pos"]) or 0.0
        # 1.0 means exactly what the position returns; below 1 is a shortfall
        rel = (pps / med) if med else 1.0
        raw_loss = p["lost"] / decided
        # shrink toward the base rate so a short sample cannot top the list
        adj_loss = (p["lost"] + SHRINK * base_loss) / (decided + SHRINK)

        row = dict(k=k, n=p["name"], pos=p["pos"],
                   owners=owners, handoffs=handoffs,
                   seasons=sorted(p["seasons"]),
                   starts=p["starts"], rostered=p["rostered"],
                   pts=_r(p["pts"]), pps=_r(pps),
                   pos_median=_r(med), rel=_r(rel, 3),
                   won=p["won"], lost=p["lost"],
                   loss_rate=_r(raw_loss, 3), adj_loss=_r(adj_loss, 3),
                   worst=p["worst"])

        if p["pos"] in STREAMED:
            streamed.append(row)
            continue
        if owners < MIN_OWNERS:
            continue
        # the score: how far under his position, times how far over the base rate.
        # Both are 0 when the player is ordinary, so an ordinary player scores 0.
        shortfall = max(0.0, 1.0 - rel)
        excess = max(0.0, adj_loss - base_loss)
        row["score"] = _r(shortfall * excess * 100 * (1 + handoffs / 10.0), 3)
        out.append(row)

    out.sort(key=lambda r: -r["score"])
    streamed.sort(key=lambda r: -r["handoffs"])
    return dict(
        base_loss_rate=_r(base_loss, 3),
        min_starts=MIN_STARTS, min_owners=MIN_OWNERS, shrink=SHRINK,
        pos_median={k: _r(v) for k, v in sorted(pos_median.items())},
        grenades=out[:TOP],
        streamed=streamed[:20],
        considered=len(out),
    )


def run(ctx, rows, stamp=None):
    data = build_grenades(ctx, rows)
    if stamp:
        data["generated"] = stamp
    # src/lib/data, not static/: the page imports this so it renders server-side
    ctx["write_json"](os.path.join(ctx["data"], "grenades.json"), data, compact=True)
    return data
