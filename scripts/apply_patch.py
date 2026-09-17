"""Idempotent edits to template files, run from a repo root. Shared by both league sites."""
import io, os, re, sys

def edit(path, old, new, count=1, optional=False):
    s = io.open(path, encoding="utf-8").read()
    if new in s:
        return
    if old not in s:
        if optional:
            print("  skip (anchor missing):", path); return
        sys.exit(f"anchor not found in {path}: {old[:60]!r}")
    s = s.replace(old, new, count)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("  edited", path)

# layout: the "which team is yours" bar under the nav
edit("src/routes/+layout.svelte",
     '\timport { Nav, Footer } from "$lib/components"',
     '\timport { Nav, Footer } from "$lib/components"\n\timport MyTeamBar from "$lib/MyTeam/MyTeamBar.svelte";')
edit("src/routes/+layout.svelte",
     "<Nav /> <!-- adds the nav (small and large) -->",
     "<Nav /> <!-- adds the nav (small and large) -->\n    <MyTeamBar />")

# manager page: YOUR TEAM badge + history charts
p = "src/lib/Managers/Manager.svelte"
edit(p, "    import ManagerAwards from './ManagerAwards.svelte';",
     "    import ManagerAwards from './ManagerAwards.svelte';\n"
     "    import ManagerHistory from '$lib/Charts/ManagerHistory.svelte';\n"
     "    import YourTeamBadge from '$lib/MyTeam/YourTeamBadge.svelte';")
edit(p, "            {viewManager.name}\n",
     "            {viewManager.name}<YourTeamBadge handle={viewManager.handle} userId={viewManager.managerID} />\n")
edit(p, "    <ManagerAwards {leagueTeamManagers}",
     "    {#if viewManager.handle}\n        <ManagerHistory handle={viewManager.handle} />\n    {/if}\n\n    <ManagerAwards {leagueTeamManagers}")

# managers list rows
p = "src/lib/Managers/ManagerRow.svelte"
edit(p, '    import {dynasty} from "$lib/utils/leagueInfo"',
     '    import {dynasty} from "$lib/utils/leagueInfo"\n    import YourTeamBadge from "$lib/MyTeam/YourTeamBadge.svelte";')
edit(p, '    <div class="name">{manager.name}</div>',
     '    <div class="name">{manager.name}<YourTeamBadge handle={manager.handle} userId={manager.managerID} size="small" /></div>')

# power rankings: explanation + template typo that throws if a rostered player is unknown
p = "src/lib/PowerRankings/PowerRankingsDisplay.svelte"
edit(p, "if(!players[rosterPlayer]) contnue;", "if(!players[rosterPlayer]) continue;", optional=True)
edit(p, "\timport BarChart from '$lib/BarChart.svelte';",
     "\timport BarChart from '$lib/BarChart.svelte';\n    import PowerRankingsExplainer from './PowerRankingsExplainer.svelte';")
edit(p, "        <BarChart {graphs} bind:curGraph={curGraph} {leagueTeamManagers} />\n    </div>",
     "        <BarChart {graphs} bind:curGraph={curGraph} {leagueTeamManagers} />\n    </div>\n    <PowerRankingsExplainer />")

# all-time page: combined table + charts at the top
p = "src/routes/all-time/+page.svelte"
edit(p, "<script>\n    export let data;",
     "<script>\n    import CombinedStandings from '$lib/Records/CombinedStandings.svelte';\n    export let data;", optional=True)
edit(p, "    <h1>All-Time Stats</h1>\n",
     "    <h1>All-Time Stats</h1>\n\n    <CombinedStandings />\n", optional=True)

# leagueInfo: managers come from the generated file
p = "src/lib/utils/leagueInfo.js"
s = io.open(p, encoding="utf-8").read()
if "managersData" not in s:
    start = s.index("export const managers = [")
    end = s.index("\n  ]", start) + len("\n  ]")
    s = ("import managersData from '$lib/data/managers.json';\n" + s[:start]
         + "// Generated weekly by scripts/update_site.py. To change a name, bio or photo,\n"
         "// edit src/lib/data/manager_overrides.json, not this file.\n"
         "export const managers = managersData;" + s[end:])
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("  edited", p)

# footer credit
p = "src/lib/Footer.svelte"
s = io.open(p, encoding="utf-8").read()
i = s.index("\t<!-- PLEASE DO NOT REMOVE THE COPYRIGHT -->") if "<!-- PLEASE DO NOT REMOVE THE COPYRIGHT -->" in s else None
j = s.find('\t<span class="creator">Created by')
cut = j if j != -1 else i
s = s[:cut] + '''\t<!-- PLEASE DO NOT REMOVE THE COPYRIGHT -->
\t<span class="copyright">&copy; 2021 - {year} <a href="https://github.com/nmelhado/league-page">League Page</a></span>
\t<br />
\t<!-- PLEASE DO NOT REMOVE THE BUILT BY -->
\t<span class="creator">Created by <a href="http://www.nmelhado.com/">Nicholas Melhado</a>, expanded on by <a href="https://github.com/Triccsters">T.J. Ricci</a></span>
</footer>
'''
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("  footer set")

# nav tabs
p = "src/lib/utils/tabs.js"
edit(p, """    {
        icon: 'article',
        label: 'Blog',
        dest: '/blog',
        key: 'blog',
    },""", """    {
        icon: 'timeline',
        label: 'Timeline',
        dest: '/timeline',
        key: 'timeline',
    },
    {
        icon: 'article',
        label: 'Recaps',
        dest: '/recaps',
        key: 'recaps',
    },""", optional=True)
edit(p, """            {
                icon: 'local_fire_department',
                label: 'Rivalry',
                dest: '/rivalry',
            },""", """            {
                icon: 'local_fire_department',
                label: 'Rivalries (all-time)',
                dest: '/rivalries',
            },
            {
                icon: 'compare_arrows',
                label: 'Head-to-Head Tool',
                dest: '/rivalry',
            },""", optional=True)
edit(p, "label: 'Rivalries (since 2014)',", "label: 'Rivalries (all-time)',", optional=True)

# records: flag seasons still in progress so a one-week PPG isn't read as a full season
p = "src/lib/Records/RecordsAndRankings.svelte"
edit(p, "\timport BarChart from '$lib/BarChart.svelte';\n",
     "\timport BarChart from '$lib/BarChart.svelte';\n"
     "    import { site } from '$lib/utils/flpHistory';\n"
     "    // games in a season record = points / PPG; a current-season row with fewer games than a full season is partial\n"
     "    const gp = (r) => (r && r.fptsPerGame ? Math.round(r.fpts / r.fptsPerGame) : 0);\n"
     "    $: fullGames = Math.max(0, ...[...(seasonLongRecords || []), ...(seasonLongLows || [])].filter(r => r.year != site.season).map(gp));\n"
     "    const partial = (r) => r.year == site.season && gp(r) < (fullGames || 99);\n")
for var in ("mostSeasonLongPoint", "leastSeasonLongPoint"):
    edit(p, "                    <Row>\n                        <Cell class=\"rank\">{ix + 1}</Cell>\n"
            f"                        <Cell class=\"cellName\" onclick={{() => gotoManager({{year: {var}.year",
         f"                    <Row class={{partial({var}) ? 'inProgress' : ''}}>\n                        <Cell class=\"rank\">{{ix + 1}}</Cell>\n"
            f"                        <Cell class=\"cellName\" onclick={{() => gotoManager({{year: {var}.year")
    edit(p, f"                        <Cell>{{{var}.year}}</Cell>",
         f"                        <Cell>{{{var}.year}}{{#if partial({var})}}<span class=\"liveTag\">in progress · {{gp({var})}} gm</span>{{/if}}</Cell>")
edit(p, "Season Points<span class=\"italic\">Ranked by PPG</span></Cell>",
     "Season Points<span class=\"italic\">Ranked by PPG · green rows are {site.season}, still in progress</span></Cell>",
     count=2)
edit(p, "<style>\n",
     "<style>\n    :global(.recordTable tr.inProgress td) { background: rgba(39, 174, 96, 0.14); }\n"
     "    :global(.recordTable tr.inProgress td:first-child) { box-shadow: inset 4px 0 0 #27ae60; }\n"
     "    .liveTag { display: block; font-size: 0.72em; font-weight: 600; color: #2ecc71; white-space: nowrap; }\n")

# record tables: mark managers who are no longer in the league ("Left league in YYYY")
p = "src/lib/Records/RecordTeam.svelte"
edit(p, "    export let leagueTeamManagers, managerID = null, rosterID = null, year, compressed = false, points = null;\n",
     "    export let leagueTeamManagers, managerID = null, rosterID = null, year, compressed = false, points = null;\n"
     "\n"
     "    // Former managers: nobody on this team is on a roster this season.\n"
     "    const tmm = leagueTeamManagers.teamManagersMap || {};\n"
     "    const cur = leagueTeamManagers.currentSeason;\n"
     "    const currentIDs = new Set(Object.values(tmm[cur] || {}).flatMap(t => t.managers || []));\n"
     "    const lastYearFor = (id) => Math.max(0, ...Object.entries(tmm)\n"
     "        .filter(([, teams]) => Object.values(teams).some(t => (t.managers || []).includes(id))).map(([y]) => +y));\n"
     "    $: ids = managerID ? [managerID] : rosterID ? (tmm[!year || year > cur ? cur : year]?.[rosterID]?.managers || []) : [];\n"
     "    $: former = currentIDs.size > 0 && ids.length > 0 && !ids.some(id => currentIDs.has(id));\n"
     "    $: leftIn = former ? Math.max(...ids.map(lastYearFor)) + 1 : null;\n")
edit(p, "        {#if !user}\n            <div class=\"managerNames\">",
     "        {#if former}\n            <div class=\"leftTag\">Left league in {leftIn}</div>\n        {/if}\n"
     "        {#if !user}\n            <div class=\"managerNames\">")
edit(p, "<style>\n",
     "<style>\n    .leftTag { display: inline-block; font-size: 0.66em; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;\n"
     "        background: #5d6d7e; color: #fff; border-radius: 3px; padding: 0.05em 0.4em; margin: 0.1em 0; white-space: nowrap; }\n")

# manager page: "in the league since" counts every platform, not just Sleeper
edit("src/lib/Managers/Manager.svelte",
     "In the league since '{datesActive.start.toString().substr(2)}",
     "In the league since '{String(Math.min(viewManager.fantasyStart || 9999, datesActive.start)).substr(2)}")
print("done")
