import { redirect } from '@sveltejs/kit';
import managers from '$lib/data/managers.json';

// T.J.'s career now lives on his manager page, built from the full game history.
export function load() {
    const me = managers.find(m => m.handle === 'triccster');
    throw redirect(307, me && me.managerID ? `/manager?manager=${encodeURIComponent(me.managerID)}` : '/managers');
}
