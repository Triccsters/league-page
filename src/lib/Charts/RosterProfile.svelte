<script>
    // The roster as it stands: who is on it, how old it is, and how it was built.
    import { onMount } from 'svelte';
    import { nameOf, site } from '$lib/utils/flpHistory';

    export let handle;

    let data = null;
    let failed = false;
    let show = 'roster';

    onMount(async () => {
        try {
            const r = await fetch('/data/rosters.json');
            if (!r.ok) throw new Error(r.status);
            data = await r.json();
        } catch (e) {
            failed = true;
        }
    });

    $: me = data?.managers?.[handle] ?? null;
    $: dynasty = !!data?.dynasty;
    $: players = me?.players ?? [];
    $: starters = players.filter(p => p.st);
    $: bench = players.filter(p => !p.st);

    const SRC = {
        draft: { icon: '🎯', label: 'Drafted' },
        trade: { icon: '🤝', label: 'Traded for' },
        waiver: { icon: '🧲', label: 'Off waivers' },
        unknown: { icon: '•', label: 'Unrecorded' },
    };
    const order = ['draft', 'trade', 'waiver', 'unknown'];

    const srcLine = (p) =>
        !p.src ? 'how he arrived is not in the records'
            : `${SRC[p.src.kind].label.toLowerCase()} ${p.src.season}${p.src.detail ? `, ${p.src.detail}` : ''}`;

    const GLAB = {
        QB: 'Quarterback', RB: 'Running backs', WR: 'Receivers', TE: 'Tight end',
        FLEX: 'Flex', SUPER_FLEX: 'Superflex', BENCH: 'Bench',
    };
    const GORDER = ['QB', 'RB', 'WR', 'TE', 'FLEX', 'SUPER_FLEX', 'BENCH'];

    $: groups = GORDER
        .filter(g => me?.groups?.[g])
        .map(g => ({ g, label: GLAB[g] ?? g, ...me.groups[g] }));

    // 1 of 12 is first; the medal is only for a real podium finish
    const medal = (r) => (r === 1 ? '🥇' : r === 2 ? '🥈' : r === 3 ? '🥉' : '');
    const ord = (n) => {
        const s = ['th', 'st', 'nd', 'rd'], v = n % 100;
        return n + (s[(v - 20) % 10] || s[v] || s[0]);
    };

    // a light age read, worded rather than scored
    $: ageRead = !me?.age?.all ? null
        : me.rank_young <= 3 ? 'one of the youngest rosters in the league'
        : me.rank_young > me.of - 3 ? 'one of the oldest rosters in the league'
        : 'middle of the league for age';
</script>

{#if me}
    <section class="rp">
        <div class="head">
            <h3>The roster right now</h3>
            <div class="tabs">
                <button class:on={show === 'roster'} onclick={() => (show = 'roster')}>Roster</button>
                <button class:on={show === 'built'} onclick={() => (show = 'built')}>How it was built</button>
                {#if groups.length}
                    <button class:on={show === 'groups'} onclick={() => (show = 'groups')}>Position groups</button>
                {/if}
                {#if me.age?.all}
                    <button class:on={show === 'age'} onclick={() => (show = 'age')}>Age</button>
                {/if}
            </div>
        </div>

        {#if me.injured?.length}
            <p class="inj">
                🚑 {me.injured.map(p => `${p.n} (${p.inj})`).join(' · ')}
            </p>
        {/if}

        {#if show === 'roster'}
            <div class="two">
                <div>
                    <h4>Starters</h4>
                    {#each starters as p}
                        <div class="row">
                            <span class="pos">{p.p}</span>
                            <span class="nm">{p.n}<small>{p.t || 'FA'}{p.age ? ` · ${p.age}` : ''}{p.inj ? ` · ${p.inj}` : ''}</small></span>
                            <span class="pt">{p.now}</span>
                        </div>
                    {:else}
                        <p class="sub">No lineup set yet.</p>
                    {/each}
                </div>
                <div>
                    <h4>Bench <small>({bench.length})</small></h4>
                    {#each bench.slice(0, 12) as p}
                        <div class="row dim">
                            <span class="pos">{p.p}</span>
                            <span class="nm">{p.n}<small>{p.t || 'FA'}{p.age ? ` · ${p.age}` : ''}{p.inj ? ` · ${p.inj}` : ''}</small></span>
                            <span class="pt">{p.now}</span>
                        </div>
                    {/each}
                </div>
            </div>
            <p class="sub">Points are what each has scored in the starting lineup this season.</p>

        {:else if show === 'built'}
            <div class="cards">
                {#each order as k}
                    {@const s = me.sources?.[k]}
                    {#if s?.n}
                        <div class="card">
                            <span class="em">{SRC[k].icon}</span>
                            <b>{s.n}</b>
                            <span class="lab">{SRC[k].label}</span>
                            <small>{Math.round(s.pts).toLocaleString()} pts returned</small>
                        </div>
                    {/if}
                {/each}
            </div>
            {#if dynasty && data.first_draft}
                <p class="sub">
                    Still holding <b>{me.startup_held}</b> from the {data.first_draft} startup draft.
                </p>
            {/if}
            <h4>Every player, and where he came from</h4>
            {#each players as p}
                <div class="row">
                    <span class="pos">{p.p}</span>
                    <span class="nm">{p.n}<small>{srcLine(p)}</small></span>
                    <span class="pt">{Math.round(p.pts)}</span>
                </div>
            {/each}
            <p class="sub">
                Points are everything he has scored while started for this manager, not just this season.
                A player traced to more than one move is credited to the most recent one.
            </p>

        {:else if show === 'groups'}
            <p class="lead">
                Every group ranked against the other {me.of - 1} teams, three ways:
                what it has scored <b>this season</b>, what it averages <b>per start</b>
                across this league's whole history, and where the <b>experts</b> rank it.
            </p>
            <div class="grp">
                {#each groups as g}
                    <div class="gcard">
                        <div class="gtop">
                            <b>{g.label}</b>
                            <small>{g.n} player{g.n === 1 ? '' : 's'}</small>
                        </div>
                        <div class="mets">
                            <div class="met">
                                <span class="mv">{medal(g.rank?.now)}{ord(g.rank?.now ?? 0)}</span>
                                <span class="ml">this season</span>
                                <small>{g.now} pts</small>
                            </div>
                            <div class="met">
                                <span class="mv">{g.rank?.rate ? medal(g.rank.rate) + ord(g.rank.rate) : '—'}</span>
                                <span class="ml">per start, all time</span>
                                <small>{g.rate ?? '—'} avg</small>
                            </div>
                            <div class="met">
                                <span class="mv">{g.rank?.ecr ? medal(g.rank.ecr) + ord(g.rank.ecr) : '—'}</span>
                                <span class="ml">expert rank</span>
                                <small>
                                    {g.ecr ?? '—'} avg
                                    {#if g.ecrtot && g.ecrn < g.ecrtot}
                                        · {g.ecrtot - g.ecrn} unranked
                                    {/if}
                                </small>
                            </div>
                        </div>
                    </div>
                {/each}
            </div>
            {#if data.ecr?.asof}
                <p class="sub">
                    Expert rank is the FantasyPros consensus for each player at his own position,
                    averaged across the group, so a lower number is better. A player nobody ranks
                    counts as one spot past the end of the list rather than being left out, which is
                    why a deep bench can rate ahead of a thin one.
                    {data.ecr.kind === 'DYNASTY' ? 'Dynasty' : 'Rest-of-season'} rankings,
                    {data.ecr.scoring === 'HALF' ? 'Half PPR' : data.ecr.scoring},
                    as of {data.ecr.asof}.
                    {#if data.ecr.kind === 'DYNASTY'}
                        Those dynasty rankings are built for one-quarterback leagues, so they
                        understate what a quarterback is worth here.
                    {/if}
                </p>
            {/if}

        {:else}
            <p class="lead">
                Starters average <b>{me.age.starters ?? '—'}</b>, whole roster <b>{me.age.all}</b>,
                league average {data.league_age}. That is {ageRead}
                ({me.rank_young} of {me.of}, youngest first).
            </p>
            <div class="two">
                <div>
                    <h4>By position</h4>
                    {#each Object.entries(me.age.byPos) as [pos, a]}
                        <div class="row"><span class="pos">{pos}</span><span class="nm">average age</span><span class="pt">{a}</span></div>
                    {/each}
                </div>
                <div>
                    <h4>By age band</h4>
                    {#each Object.entries(me.age.buckets) as [band, n]}
                        <div class="row">
                            <span class="nm">{band}</span>
                            <span class="bar"><span class="fill" style="width:{Math.min(100, n * 12)}%"></span></span>
                            <span class="pt">{n}</span>
                        </div>
                    {/each}
                </div>
            </div>
            {#if me.age.oldest && me.age.youngest}
                <p class="sub">
                    Oldest: {me.age.oldest.n} ({me.age.oldest.age}) ·
                    Youngest: {me.age.youngest.n} ({me.age.youngest.age})
                </p>
            {/if}
        {/if}
    </section>
{:else if failed}
    <p class="sub err">Roster data could not be loaded.</p>
{/if}

<style>
    .rp { max-width: 900px; margin: 1.4em auto 0; padding: 0 1em; text-align: left; }
    .head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.6em; margin-bottom: 0.5em; }
    h3 { margin: 0; font-size: 1em; }
    h4 { margin: 0.8em 0 0.2em; font-size: 0.82em; text-transform: uppercase;
         letter-spacing: 0.04em; opacity: 0.65; }
    h4 small { text-transform: none; letter-spacing: 0; opacity: 0.7; }
    .tabs { display: flex; gap: 0.3em; }
    button { font: inherit; font-size: 0.78em; padding: 0.2em 0.65em; border-radius: 999px;
             border: 1px solid rgba(127,127,127,0.4); background: transparent; color: inherit; cursor: pointer; }
    button.on { border-color: #3498db; background: rgba(52,152,219,0.16); font-weight: 600; }
    .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0 1.6em; }
    .row { display: grid; grid-template-columns: 2.6em 1fr auto; gap: 0.5em; align-items: baseline;
           padding: 0.22em 0; border-bottom: 1px solid rgba(127,127,127,0.14); font-size: 0.88em; }
    .row.dim { opacity: 0.72; }
    .pos { opacity: 0.6; font-size: 0.78em; }
    .nm small { display: block; opacity: 0.6; font-size: 0.78em; }
    .pt { font-variant-numeric: tabular-nums; font-weight: 600; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.6em; margin: 0.4em 0; }
    .card { border: 1px solid rgba(127,127,127,0.28); border-radius: 9px; padding: 0.5em 0.7em; }
    .card .em { font-size: 1.1em; }
    .card b { font-size: 1.3em; margin-left: 0.25em; }
    .card .lab { display: block; font-size: 0.8em; opacity: 0.75; }
    .card small { display: block; font-size: 0.75em; opacity: 0.6; }
    .lead { font-size: 0.95em; margin: 0.3em 0 0.6em; }
    .inj { font-size: 0.85em; margin: 0 0 0.5em; color: #e67e22; }
    .sub { opacity: 0.65; font-size: 0.8em; margin: 0.5em 0 0; }
    .err { color: #e74c3c; }
    .grp { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.6em; margin: 0.4em 0; }
    .gcard { border: 1px solid rgba(127,127,127,0.28); border-radius: 9px; padding: 0.55em 0.75em; }
    .gtop { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5em;
            padding-bottom: 0.4em; border-bottom: 1px solid rgba(127,127,127,0.18); }
    .gtop small { opacity: 0.6; font-size: 0.78em; }
    .mets { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.4em; padding-top: 0.45em; }
    .met { text-align: center; }
    .mv { display: block; font-size: 1.05em; font-weight: 700; font-variant-numeric: tabular-nums; }
    .ml { display: block; font-size: 0.7em; opacity: 0.72; line-height: 1.2; }
    .met small { display: block; font-size: 0.7em; opacity: 0.55; font-variant-numeric: tabular-nums; }
    .bar { height: 8px; border-radius: 99px; background: rgba(127,127,127,0.2); overflow: hidden; align-self: center; }
    .fill { display: block; height: 100%; background: #3498db; }
</style>
