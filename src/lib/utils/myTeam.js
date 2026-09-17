// "Which team is yours?" The site has no login, so the visitor picks their team
// once and it is remembered on that device (localStorage). Stored value is the
// Sleeper handle used in history.json / managers.json.
import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import managersData from '$lib/data/managers.json';

const KEY = 'myTeamHandle';

const initial = () => {
    if (!browser) return null;
    try { return localStorage.getItem(KEY); } catch { return null; }
};

export const myTeam = writable(initial());

myTeam.subscribe((v) => {
    if (!browser) return;
    try {
        if (v) localStorage.setItem(KEY, v);
        else localStorage.removeItem(KEY);
    } catch { /* private mode: remember for this visit only */ }
});

export const myManagers = managersData;

// Managers-page index for a handle, for links like /manager?manager=N
export const managerIndex = (handle) => managersData.findIndex(m => m.handle === handle);

export const handleForUser = (userId) => managersData.find(m => m.managerID === userId)?.handle || null;
