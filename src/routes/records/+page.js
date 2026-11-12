import { redirect } from '@sveltejs/kit';

// The original Records page read Sleeper only (2021 on). The Record Book covers every
// season on Yahoo and Sleeper, with an era toggle for the Sleeper years (T.J., 2026-11-12).
export function load() {
    throw redirect(308, '/record-book');
}
