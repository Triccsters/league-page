# Weekly site update

Run on tricclt from the repo folder, any time after Monday night's game is final:

```
python scripts/update_site.py --push
```

That one command:

1. Rebuilds `src/lib/data/history.json` with every FL Players game since 2014
   (Yahoo 2014-2020 and Sleeper 2021-2025 from the vault's `flp.py`, the current
   season live from Sleeper).
2. Writes a recap for each finished week that doesn't have one yet, and
   rebuilds the latest week in case Sleeper corrected a score.
3. Commits and pushes. Vercel redeploys the site on its own.

Leave off `--push` to look at the changes first. `--week 3` rebuilds one week;
`--all` rebuilds every week.

## Adding your own words or a video to a recap

Open `src/lib/data/recaps/2026-wNN.json` and fill in any of these. The script
never overwrites them:

- `"title"`: replaces "Week N recap"
- `"intro"`: your write-up. Leave a blank line between paragraphs.
- `"video"`: a YouTube, Vimeo or Google Drive share link, or a link to an .mp4
- `"notes"`: a list of talking points, e.g. `["Joey is 8-0 against T.J. since 2021"]`

Then run `python scripts/update_site.py --push` (or commit the file yourself).

**Video hosting:** use an unlisted YouTube upload or a Google Drive link shared
as "anyone with the link". Don't put video files in this repo; GitHub and
Vercel both have file-size limits that a weekly show will hit quickly.

## When the season rolls over

Change `LEAGUE_ID` and `SEASON` at the top of `update_site.py`, and `leagueID`
in `src/lib/utils/leagueInfo.js`, to the new Sleeper league.
