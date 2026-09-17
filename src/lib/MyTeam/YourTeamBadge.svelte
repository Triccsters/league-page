<script>
    // Shows "YOUR TEAM" when the given Sleeper handle (or user id) is the visitor's pick.
    import { onMount } from 'svelte';
    import { myTeam, handleForUser } from '$lib/utils/myTeam';
    export let handle = null;
    export let userId = null;
    export let size = 'normal';   // 'normal' | 'small'
    let ready = false;
    onMount(() => { ready = true; });
    $: h = handle || (userId && handleForUser(userId));
</script>

{#if ready && h && $myTeam === h}
    <span class="yours {size}">YOUR TEAM</span>
{/if}

<style>
    .yours {
        display: inline-block; vertical-align: middle;
        background: #27ae60; color: #fff; font-weight: 700; letter-spacing: 0.04em;
        border-radius: 4px; padding: 0.15em 0.55em; font-size: 0.75rem; margin: 0 0.4em;
        white-space: nowrap;
    }
    .small { font-size: 0.62rem; padding: 0.1em 0.4em; }
</style>
