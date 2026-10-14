<script>
	import { goto } from '$app/navigation';
    import { managers } from '$lib/utils/helper';
	import { tabs } from '$lib/utils/tabs';
	import { site } from '$lib/utils/flpHistory';
	import { onMount } from 'svelte';

	let outOfDate = false;

    let el, footerHeight;

    let innerWidth;

    const resize = (e, delay) => {
        const bottom = el?.getBoundingClientRect().bottom;
        const top = el?.getBoundingClientRect().top;
        if(delay) {
            setTimeout(() => {
                resize(e, false);
            }, 100)
        } else {
            footerHeight = bottom - top;
        }
    }

	onMount(async () => {
		const res = await fetch('/api/checkVersion', {compress: true})
		const needUpdate = await res.json();
		outOfDate = needUpdate;
        resize(el?.getBoundingClientRect(), true);
	})

    let managersOutOfDate = false;
    if(managers) {
        for(const manager of managers) {
            if(manager.roster && !manager.managerID) {
                managersOutOfDate = true;
                resize(el?.getBoundingClientRect(), true);
                break;
            }
        }
    }

	const year = new Date().getFullYear();

	const FOOTER = ['/', '/matchups', '/standings', '/insights', '/rules'];
	const allLinks = tabs.flatMap(t => (t.nest ? t.children : [t]));
	const footerLinks = FOOTER.map(d => allLinks.find(c => c.dest === d)).filter(Boolean);

    $: resize(el?.getBoundingClientRect(), false, innerWidth);
</script>

<svelte:window bind:innerWidth={innerWidth} />

<style>
	footer {
		background-color: var(--f8f8f8);
		width: 100%;
        display: block;
        position: absolute;
        bottom: 0;
		z-index: 1;
		border-top: 1px solid #920505;
		padding: 30px 0 60px;
		text-align: center;
		color: #777;
	}

	#navigation {
		margin: 0 0 2em;
	}

	#navigation ul {
		margin: 0;
		padding: 0;
	}

	#navigation ul li {
		list-style-type: none;
		display: inline;
	}

	#navigation li:not(:first-child):before {
		content: " | ";
	}

	.navLink {
		display: inline-block;
		cursor: pointer;
		padding: 6px 10px;
	}

	.navLink:hover {
		color: #920505;
	}

	.updateNotice {
		color: var(--g999);
		font-style: italic;
		font-size: 0.8em;
		margin-top: 0;
	}
</style>

<div class="footerSpacer" style="height: {footerHeight}px;" />

<!-- footer with update notice -->
<footer bind:this={el}>
	<div id="navigation">
		<ul>
			<!-- a short list: the full menu is at the top of every page -->
			{#each footerLinks as l}
				<li><div class="navLink" onclick={() => goto(l.dest)}>{l.label}</div></li>
			{/each}
		</ul>
	</div>
	<span class="copyright">{site.league_name} · est. {site.first_season}</span>
	<br />
	<!-- template credit kept (the template asks for it), just quieter than the old "© League Page" line -->
	<span class="creator">Built on <a href="https://github.com/nmelhado/league-page">League Page</a> by <a href="http://www.nmelhado.com/">Nicholas Melhado</a>, expanded by <a href="https://triccsters.vercel.app">T.J. Ricci</a></span>
</footer>
