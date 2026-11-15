// Hall of Fame and Trophy Room are one page now (T.J., 2026-11-15). Old links still work.
import { redirect } from '@sveltejs/kit';

export function load() {
    redirect(307, '/awards');
}
