<script>
    // One way to show a manager everywhere: the name (first name in FL Players,
    // the Sleeper handle elsewhere, the team name on ESPN), with this season's
    // team name in small text under it when it says something different.
    import { nameOf, teamName, managerLink, site } from '$lib/utils/flpHistory';

    let { h, season = site.season, link = true, bold = false } = $props();

    const name = $derived(nameOf(h));
    const team = $derived.by(() => {
        const t = (teamName(season, h) || '').trim();
        return t && t !== h && t !== name ? t : null;
    });
    const href = $derived(link ? managerLink(h) : null);
</script>

<span class="who" class:bold>
    {#if href}<a {href}>{name}</a>{:else}<span>{name}</span>{/if}
    {#if team}<small class="tn">{team}</small>{/if}
</span>

<style>
    .who { display: inline-flex; flex-direction: column; line-height: 1.15; vertical-align: top; min-width: 0; max-width: 100%; }
    .bold { font-weight: 700; }
    .tn { font-size: 0.72em; font-weight: 400; opacity: 0.65; overflow-wrap: anywhere; }
    a { color: #3498db; }
</style>
