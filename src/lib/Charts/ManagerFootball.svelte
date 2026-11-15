<script>
    // This manager's real football totals and where they rank (T.J., 2026-11-13).
    import { onMount } from 'svelte';
    import { currentManagers } from '$lib/utils/flpHistory';
    export let handle;

    let data = null;
    onMount(async () => {
        try { data = await fetch('/data/football.json').then(r => r.json()); } catch (e) { data = null; }
    });
    const TILES = [['pass_yd', 'Passing yards'], ['rush_yd', 'Rushing yards'], ['rec_yd', 'Receiving yards'], ['rec', 'Catches'], ['td', 'Touchdowns'], ['pass_int', 'Interceptions']];
    const full = (r) => ({ ...r, td: r.pass_td + r.rush_td + r.rec_td });
    const ord = (n) => n + (n % 100 >= 11 && n % 100 <= 13 ? 'th' : ['th', 'st', 'nd', 'rd'][n % 10] || 'th');
    $: me = data?.managers?.[handle] ? full(data.managers[handle].tot) : null;
    $: field = !data ? [] : currentManagers.filter(h => data.managers[h]).map(h => full(data.managers[h].tot));
    $: rank = (k) => 1 + field.filter(v => v[k] > me[k]).length;
    $: nSeasons = data?.managers?.[handle] ? Object.keys(data.managers[handle].seasons).length : 0;
</script>

{#if me}
    <section class="mf">
        <p class="eyebrow">Football stats</p>
        <h3>What this team's starters actually did</h3>
        <p class="sub">Real yards, catches and touchdowns from players in the starting lineup, {nSeasons} season{nSeasons === 1 ? '' : 's'} on Sleeper ({data.seasons[0]} on). Rank is among the {field.length} current managers.</p>
        <div class="tiles">
            {#each TILES as [k, label]}
                <div class="tile"><span>{label}</span><b>{me[k].toLocaleString('en-US')}</b><small>{ord(rank(k))} of {field.length}</small></div>
            {/each}
        </div>
        <p class="more"><a href="/football">Football stats for every manager</a></p>
    </section>
{/if}

<style>
    .mf { max-width: 900px; margin: 0.5em auto 2em; padding: 0 1em; text-align: left; }
    .eyebrow { color: #ff7a2f; font-size: 0.75em; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin: 0; }
    h3 { margin: 0.1em 0; font-size: 1.15em; }
    .sub { opacity: 0.72; font-size: 0.84em; margin: 0 0 0.7em; }
    .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(135px, 1fr)); gap: 0.5em; }
    .tile { background: #131a2a; color: #e8edf5; border: 1px solid #25304a; border-top: 3px solid #ff7a2f; border-radius: 12px; padding: 0.55em 0.7em; }
    .tile span { font-size: 0.66em; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: #9fb0cc; }
    .tile b { display: block; font-size: 1.45em; line-height: 1.15; color: #fff; font-variant-numeric: tabular-nums; }
    .tile small { color: #c6d2e6; font-size: 0.78em; }
    .more { margin-top: 0.8em; font-size: 0.9em; }
    .more a { color: #3498db; }
</style>
