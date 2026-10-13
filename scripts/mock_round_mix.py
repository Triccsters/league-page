"""
Add the league's real round-by-round position mix to the mock draft data.

Reads every draft listed in static/data/mock_draft.json (profileDrafts) from
Sleeper and writes roundMix: for each round, how many QB/RB/WR/TE/K/DEF this
league actually took, summed over those drafts. The mock draft page turns it
into the "this part of the draft" card.

Run on TriccLT (Sleeper is not reachable from the Claude cloud container):
  python scripts/mock_round_mix.py
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "static", "data", "mock_draft.json")
POS = ["QB", "RB", "WR", "TE", "K", "DEF"]


def get(path):
    req = urllib.request.Request("https://api.sleeper.app/v1" + path,
                                 headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    rounds = data["league"]["rounds"]
    mix = [{p: 0 for p in POS} for _ in range(rounds)]
    used = []
    for d in data["profileDrafts"]:
        picks = get("/draft/%s/picks" % d["draftId"])
        for p in picks:
            pos = (p.get("metadata") or {}).get("position")
            r = int(p["round"])
            if pos in POS and 1 <= r <= rounds:
                mix[r - 1][pos] += 1
        used.append(d["season"])
    data["roundMix"] = {"seasons": used, "rounds": mix}
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    for i, m in enumerate(mix, 1):
        print(i, m)


if __name__ == "__main__":
    main()
