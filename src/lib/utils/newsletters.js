// Written newsletter issues, one JSON per week in src/lib/data/newsletter/.
// The build never writes these; a site with no folder simply has none.
const files = import.meta.glob('/src/lib/data/newsletter/*.json', { eager: true, import: 'default' });

export const newsletters = Object.values(files).filter((x) => x && x.slug);
export const newsletterFor = (slug) => newsletters.find((x) => x.slug === slug) || null;
