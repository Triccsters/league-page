import { redirect } from '@sveltejs/kit';

// The old sample constitution now lives at /rules
export function load() {
    throw redirect(308, '/rules');
}
