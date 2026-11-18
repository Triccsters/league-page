<script>
    // Inline links inside newsletter feature text.
    //
    // Write [label](/standings) or [label](https://example.com) anywhere in a
    // feature block's text, a list item or a table cell and it renders as a
    // real link. Everything else stays plain text: the issue JSON can never
    // inject markup, because nothing here goes through the html directive.
    //
    // Added 2026-11-18. Before this, every feature block rendered as escaped
    // text, so links written into an issue died silently.
    export let t = '';
    const parse = (s) => {
        const re = /\[([^\]\n]+)\]\((\/[^\s)]*|https?:\/\/[^\s)]+)\)/g;
        const out = [];
        let i = 0, m;
        while ((m = re.exec(s)) !== null) {
            if (m.index > i) out.push({ text: s.slice(i, m.index) });
            out.push({ text: m[1], href: m[2] });
            i = m.index + m[0].length;
        }
        if (i < s.length) out.push({ text: s.slice(i) });
        return out;
    };
    $: parts = parse(String(t ?? ''));
</script>

{#each parts as p}{#if p.href}{#if p.href.startsWith('http')}<a class="rl" href={p.href} target="_blank" rel="noopener noreferrer">{p.text}</a>{:else}<a class="rl" href={p.href}>{p.text}</a>{/if}{:else}{p.text}{/if}{/each}

<style>
    .rl { color: inherit; text-decoration: underline; text-underline-offset: 2px; text-decoration-thickness: 1px; }
    .rl:hover { opacity: 0.75; }
</style>
