<script>
	import { tabs } from '$lib/utils/tabs';
	import Tab, { Icon, Label } from '@smui/tab';
	import List, { Item, Graphic, Text, Separator } from '@smui/list';
	import TabBar from '@smui/tab-bar';
    import { page } from '$app/state';
	import { goto, preloadData } from '$app/navigation';
	import { enableBlog, managers } from '$lib/utils/leagueInfo';

	let active = $state(tabs.find(tab => tab.dest == page.url.pathname || (tab.nest && tab.children.find(subTab => subTab.dest == page.url.pathname))));

	// several menus can be nested now, so the open one is tracked by key and the
	// dropdown is positioned under whichever tab was clicked
	let openKey = $state(null);
	const els = {};
	let display = $derived(!!openKey);
	let width = $state(0);
	let height = $state(0);
	let left = $state(0);
	let top = $state(0);

	const place = (node) => {
		const r = node?.getBoundingClientRect?.();
		if (!r) return;
		top = r.top;
		height = r.bottom - r.top + 1;
		// the menu is at least wide enough for its own labels
		width = Math.max(r.right - r.left, 210);
		left = Math.min(r.left, window.innerWidth - width - 8);
	};

	let innerWidth = $state();

	const open = (tab, e) => {
		// SMUI's Tab does not always hand back a DOM event, so fall back to
		// finding the rendered tab by its label
		let node = e?.currentTarget?.closest?.('.mdc-tab') || e?.target?.closest?.('.mdc-tab');
		if (!node && typeof document !== 'undefined') {
			node = [...document.querySelectorAll('.navBar .mdc-tab')]
				.find(t => t.textContent.includes(tab.label));
		}
		place(node);
		openKey = openKey === tab.key ? null : tab.key;
	}

	const subGoto = (dest) => {
		openKey = null;
		goto(dest);
	}

	let tabChildren = $derived(openKey ? (tabs.find(t => t.key === openKey)?.children ?? []) : []);

</script>

<svelte:window bind:innerWidth={innerWidth} />

<style>
    :global(.navBar) {
		display: inline-flex;
		position: relative;
    	justify-content: center;
    }

	:global(.navBar .material-icons) {
		font-size: 1.8em;
		height: 25px;
		width: 22px;
	}

	.parent {
		position: relative;
	}

	.subMenu {
		overflow-y: hidden;
		display: block;
		position: absolute;
		z-index: 5;
		background-color: var(--fff);
		transition: all 0.4s;
	}

	.overlay {
		display: block;
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		height: 100vh;
		z-index: 4;
	}

	:global(.mdc-deprecated-list) {
		padding: 0;
	}

	:global(.subText) {
		font-size: 0.8em;
	}

	:global(.dontDisplay) {
		display: none;
	}
</style>

<div tabindex="0" role="button" class="overlay" style="display: {display ? "block" : "none"};" onclick={() => (openKey = null)}></div>

<div class="parent">
	<TabBar class="navBar" {tabs} key={(tab) => tab.key} bind:active>
		{#snippet tab(tab)}
			{#if tab.nest}
				<div bind:this={els[tab.key]}>
					<Tab
						{tab}
						minWidth
						onclick={(e) => open(tab, e)}
					>
						<Icon class="material-icons">{tab.icon}</Icon>
						<Label>{tab.label}</Label>
					</Tab>
				</div>
			{:else}
				<Tab
					class="{tab.label == 'Blog' && !enableBlog ? 'dontDisplay' : ''}"
					{tab}
					onTouchstart={() => preloadData(tab.dest)}
					onMouseover={() => preloadData(tab.dest)}
					href={tab.dest}
					minWidth
				>
					<Icon class="material-icons">{tab.icon}</Icon>
					<Label>{tab.label}</Label>
				</Tab>
			{/if}
		{/snippet}
	</TabBar>
	<div class="subMenu" style="max-height: {display ? 49 * tabChildren.length - 1 - (managers.length ? 0 : 48) : 0}px; width: {width}px; top: {height}px; left: {left}px; box-shadow: 0 0 {display ? "3px" : "0"} 0 #00316b; border: {display ? "1px" : "0"} solid #00316b; border-top: none;">
		<List>
			{#each tabChildren as subTab, ix}
				{#if subTab.label == 'Managers'}
					<Item class="{managers.length ? '' : 'dontDisplay'}" onSMUIAction={() => subGoto(subTab.dest)} ontouchstart={() => preloadData(subTab.dest)} onmouseover={() => preloadData(subTab.dest)}>
						<Graphic class="material-icons">{subTab.icon}</Graphic>
						<Text class="subText">{subTab.label}</Text>
					</Item>
					{#if ix != tabChildren.length - 1}
						<Separator />
					{/if}
				{:else}
					<Item onSMUIAction={() => subGoto(subTab.dest)} ontouchstart={() => {if(subTab.label != 'Go to Sleeper') preloadData(subTab.dest)}} onmouseover={() => {if(subTab.label != 'Go to Sleeper') preloadData(subTab.dest)}}>
						<Graphic class="material-icons">{subTab.icon}</Graphic>
						<Text class="subText">{subTab.label}</Text>
					</Item>
					{#if ix != tabChildren.length - 1}
						<Separator />
					{/if}
				{/if}
			{/each}
		</List>
	</div>
</div>
