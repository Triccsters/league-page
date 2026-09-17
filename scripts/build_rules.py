"""League rules straight from Sleeper, plus every setting that changed between seasons.

Writes src/lib/data/rules.json. Anything Sleeper doesn't store (payouts, trade
etiquette, rules from before Sleeper) goes in src/lib/data/rules_extra.json by hand.
"""
from collections import Counter

SCORING = {
    "pass_yd": "Passing yard", "pass_td": "Passing TD", "pass_int": "Interception thrown",
    "pass_2pt": "Passing 2-pt", "pass_int_td": "Pick-six thrown", "pass_sack": "Sacked",
    "pass_cmp": "Completion", "pass_inc": "Incompletion", "pass_att": "Pass attempt",
    "pass_cmp_40p": "40+ yd completion", "pass_td_40p": "40+ yd passing TD",
    "rush_yd": "Rushing yard", "rush_td": "Rushing TD", "rush_2pt": "Rushing 2-pt",
    "rush_att": "Rush attempt", "rush_40p": "40+ yd rush", "rush_td_40p": "40+ yd rushing TD",
    "rush_fd": "Rushing first down",
    "rec": "Reception", "rec_yd": "Receiving yard", "rec_td": "Receiving TD", "rec_2pt": "Receiving 2-pt",
    "rec_40p": "40+ yd reception", "rec_td_40p": "40+ yd receiving TD", "rec_fd": "Receiving first down",
    "bonus_rec_te": "TE reception bonus", "bonus_rec_rb": "RB reception bonus", "bonus_rec_wr": "WR reception bonus",
    "bonus_pass_yd_300": "300+ passing yd bonus", "bonus_pass_yd_400": "400+ passing yd bonus",
    "bonus_rush_yd_100": "100+ rushing yd bonus", "bonus_rush_yd_200": "200+ rushing yd bonus",
    "bonus_rec_yd_100": "100+ receiving yd bonus", "bonus_rec_yd_200": "200+ receiving yd bonus",
    "bonus_pass_cmp_25": "25+ completions bonus", "bonus_rush_att_20": "20+ carries bonus",
    "fum": "Fumble", "fum_lost": "Fumble lost", "fum_rec_td": "Fumble recovery TD",
    "st_td": "Special teams TD", "st_ff": "Special teams forced fumble", "st_fum_rec": "Special teams fumble recovery",
    "kr_yd": "Kick return yard", "pr_yd": "Punt return yard",
    "xpm": "Extra point made", "xpmiss": "Extra point missed",
    "fgm_0_19": "FG 0-19", "fgm_20_29": "FG 20-29", "fgm_30_39": "FG 30-39", "fgm_40_49": "FG 40-49",
    "fgm_50p": "FG 50+", "fgm_50_59": "FG 50-59", "fgm_60p": "FG 60+", "fgmiss": "FG missed",
    "fgmiss_0_19": "FG missed 0-19", "fgmiss_20_29": "FG missed 20-29", "fgmiss_30_39": "FG missed 30-39",
    "fgmiss_40_49": "FG missed 40-49", "fgmiss_50p": "FG missed 50+", "fgm_yds": "FG yard", "fgm": "FG made",
    "def_td": "Defense TD", "def_st_td": "Defense/ST TD", "sack": "Sack", "int": "Interception",
    "ff": "Forced fumble", "fum_rec": "Fumble recovery", "safe": "Safety", "blk_kick": "Blocked kick",
    "def_st_ff": "Def/ST forced fumble", "def_st_fum_rec": "Def/ST fumble recovery", "def_2pt": "Defensive 2-pt return",
    "def_4_and_stop": "4th down stop", "def_3_and_out": "3 and out", "def_forced_punts": "Forced punt",
    "pts_allow_0": "0 points allowed", "pts_allow_1_6": "1-6 points allowed", "pts_allow_7_13": "7-13 points allowed",
    "pts_allow_14_20": "14-20 points allowed", "pts_allow_21_27": "21-27 points allowed",
    "pts_allow_28_34": "28-34 points allowed", "pts_allow_35p": "35+ points allowed",
    "yds_allow_0_100": "0-99 yards allowed", "yds_allow_100_199": "100-199 yards allowed",
    "yds_allow_200_299": "200-299 yards allowed", "yds_allow_300_349": "300-349 yards allowed",
    "yds_allow_350_399": "350-399 yards allowed", "yds_allow_400_449": "400-449 yards allowed",
    "yds_allow_450_499": "450-499 yards allowed", "yds_allow_500_549": "500-549 yards allowed",
    "yds_allow_550p": "550+ yards allowed", "tkl": "Tackle", "tkl_solo": "Solo tackle", "tkl_ast": "Assisted tackle",
    "tkl_loss": "Tackle for loss", "qb_hit": "QB hit", "pass_def": "Pass defended",
}
POS_ORDER = ["QB", "RB", "WR", "TE", "FLEX", "WRRB_FLEX", "REC_FLEX", "SUPER_FLEX", "K", "DEF",
             "DL", "LB", "DB", "IDP_FLEX", "BN"]
POS_NAME = {"FLEX": "Flex (RB/WR/TE)", "WRRB_FLEX": "Flex (RB/WR)", "REC_FLEX": "Flex (WR/TE)",
            "SUPER_FLEX": "Superflex (QB/RB/WR/TE)", "BN": "Bench", "DEF": "Team defense",
            "K": "Kicker", "IDP_FLEX": "IDP flex"}
LEAGUE_TYPE = {0: "Redraft", 1: "Keeper", 2: "Dynasty"}
WAIVER_TYPE = {0: "Rolling waivers", 1: "Reverse standings", 2: "FAAB bidding"}
PLAYOFF_TYPE = {0: "Standard bracket", 1: "Two-week championship", 2: "Two-week playoff rounds"}


def _settings(league):
    s = league.get("settings") or {}
    out = [
        ("League type", LEAGUE_TYPE.get(s.get("type"), s.get("type"))),
        ("Teams", league.get("total_rosters")),
        ("Weekly median game", "Yes, every team also plays the league median" if s.get("league_average_match") else "No"),
        ("Playoff teams", s.get("playoff_teams")),
        ("Playoffs start", f"Week {s.get('playoff_week_start')}" if s.get("playoff_week_start") else None),
        ("Playoff format", PLAYOFF_TYPE.get(s.get("playoff_round_type"), None)),
        ("Trade deadline", f"Week {s['trade_deadline']}" if s.get("trade_deadline") and s["trade_deadline"] < 99 else "None"),
        ("Waivers", WAIVER_TYPE.get(s.get("waiver_type"), s.get("waiver_type"))),
        ("FAAB budget", f"${s['waiver_budget']}" if s.get("waiver_type") == 2 else None),
        ("Waiver period", f"{s.get('waiver_clear_days')} day(s)" if s.get("waiver_clear_days") is not None else None),
        ("IR slots", s.get("reserve_slots")),
        ("Taxi squad", f"{s.get('taxi_slots')} slots" if s.get("taxi_slots") else None),
        ("Keepers", s.get("max_keepers") if s.get("type") == 1 else None),
    ]
    return [(k, v) for k, v in out if v not in (None, "")]


def _lineup(league):
    c = Counter(league.get("roster_positions") or [])
    keys = sorted(c, key=lambda p: POS_ORDER.index(p) if p in POS_ORDER else 99)
    return [(POS_NAME.get(p, p), c[p]) for p in keys]


def _scoring(league):
    sc = league.get("scoring_settings") or {}
    order = list(SCORING)
    keys = sorted((k for k, v in sc.items() if v), key=lambda k: order.index(k) if k in order else 999)
    return {SCORING.get(k, k): round(sc[k], 3) for k in keys}


def _fmt_pts(v):
    if v is None:
        return "off"
    return f"{v:g} pts"


def _diff(old, new):
    changes = []
    so, sn = dict(_settings(old)), dict(_settings(new))
    for k in sorted(set(so) | set(sn)):
        if so.get(k) != sn.get(k):
            changes.append({"area": "Settings", "what": k, "from": str(so.get(k, "none")), "to": str(sn.get(k, "none"))})
    lo, ln = dict(_lineup(old)), dict(_lineup(new))
    for k in sorted(set(lo) | set(ln)):
        if lo.get(k) != ln.get(k):
            changes.append({"area": "Lineup", "what": k, "from": str(lo.get(k, 0)), "to": str(ln.get(k, 0))})
    co, cn = _scoring(old), _scoring(new)
    for k in sorted(set(co) | set(cn)):
        if co.get(k) != cn.get(k):
            changes.append({"area": "Scoring", "what": k, "from": _fmt_pts(co.get(k)), "to": _fmt_pts(cn.get(k))})
    return changes


def build_rules(league_id, sleeper, extra_path, out_path, write_json, read_json):
    chain = []
    lid = league_id
    while lid and lid != "0":
        lg = sleeper(f"/league/{lid}")
        chain.append(lg)
        lid = lg.get("previous_league_id")
    chain.reverse()                      # oldest first
    cur = chain[-1]
    history = []
    for old, new in zip(chain, chain[1:]):
        ch = _diff(old, new)
        history.append({"season": int(new["season"]), "changes": ch})
    history.reverse()                    # newest first
    extra = read_json(extra_path, None)
    if extra is None:
        extra = {
            "_how_to": "Add league rules Sleeper doesn't track (payouts, trade rules, tiebreakers) to 'rules', "
                       "and older rule changes (e.g. from before Sleeper) to 'changes'. Each rule: "
                       "{\"title\": \"...\", \"text\": \"...\"}. Each change: {\"season\": 2019, \"text\": \"...\"}.",
            "rules": [], "changes": []}
        write_json(extra_path, extra)
    rules = {
        "league_name": cur.get("name"), "season": int(cur["season"]),
        "first_sleeper_season": int(chain[0]["season"]),
        "settings": [{"name": k, "value": v} for k, v in _settings(cur)],
        "lineup": [{"name": k, "count": v} for k, v in _lineup(cur)],
        "scoring": [{"name": k, "points": v} for k, v in _scoring(cur).items()],
        "history": history,
    }
    write_json(out_path, rules)
    return rules
