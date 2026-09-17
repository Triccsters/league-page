<script>
    import { onMount } from 'svelte';
    import { myTeam, myManagers, managerIndex } from '$lib/utils/myTeam';

    let ready = false;      // localStorage is only readable in the browser
    let picking = false;
    onMount(() => { ready = true; });

    $: me = myManagers.find(m => m.handle === $myTeam);
    const choose = (e) => {
        myTeam.set(e.target.value || null);
        picking = false;
    };
</script>

{#if ready}
    <div class="bar">
        {#if me && !picking}
            <img src={me.photo} alt="" />
            <span>Viewing as <b>{me.name}</b></span>
            <a href="/manager?manager={managerIndex(me.handle)}">Your page</a>
            <a href="/rivalries?who={me.handle}">Your rivalries</a>
            <button on:click={() => (picking = true)}>Change</button>
        {:else}
            <label>
                <span>Which team is yours?</span>
                <select on:change={choose} value={$myTeam || ''}>
                    <option value="">Pick your name…</option>
                    {#each myManagers as m}<option value={m.handle}>{m.name}</option>{/each}
                </select>
            </label>
            {#if me}<button on:click={() => (picking = false)}>Cancel</button>{/if}
            <small>Remembered on this device only, so the site can mark YOUR TEAM.</small>
        {/if}
    </div>
{/if}

<style>
    .bar {
        display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
        gap: 0.4em 1em; padding: 0.45em 1em; font-size: 0.9em;
        background: rgba(52, 152, 219, 0.12); border-bottom: 1px solid rgba(52, 152, 219, 0.35);
        position: relative; z-index: 2;
    }
    img { width: 26px; height: 26px; border-radius: 50%; object-fit: cover; }
    a { color: #3498db; }
    select, button { font-size: 0.95em; padding: 0.2em 0.5em; margin-left: 0.4em; }
    small { opacity: 0.65; }
</style>
