// Weekly recaps written by scripts/update_site.py (src/lib/data/recaps/*.json).
const files = import.meta.glob('/src/lib/data/recaps/*.json', { eager: true, import: 'default' });

export const recaps = Object.entries(files)
    .filter(([path]) => !path.endsWith('/index.json'))
    .map(([, r]) => r)
    .sort((a, b) => (b.season - a.season) || (b.week - a.week));

export const recapBySlug = (slug) => recaps.find(r => r.slug === slug) || null;

// Turns a YouTube / Vimeo / Google Drive link into an embeddable URL.
// Anything ending in a video file extension is played with <video>.
export const videoEmbed = (url) => {
    if (!url) return null;
    let m = url.match(/(?:youtube\.com\/(?:watch\?v=|shorts\/|live\/)|youtu\.be\/)([\w-]{11})/);
    if (m) return { kind: 'iframe', src: `https://www.youtube-nocookie.com/embed/${m[1]}` };
    m = url.match(/vimeo\.com\/(\d+)/);
    if (m) return { kind: 'iframe', src: `https://player.vimeo.com/video/${m[1]}` };
    m = url.match(/drive\.google\.com\/file\/d\/([\w-]+)/);
    if (m) return { kind: 'iframe', src: `https://drive.google.com/file/d/${m[1]}/preview` };
    if (/\.(mp4|webm|mov)(\?|$)/i.test(url)) return { kind: 'video', src: url };
    return { kind: 'link', src: url };
};
