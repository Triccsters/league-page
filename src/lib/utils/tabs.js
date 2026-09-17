import {leagueID} from '$lib/utils/leagueInfo';

export const tabs = [
    {
        icon: 'home',
        label: 'Home',
        dest: '/',
        key: 'home',
    },
    {
        icon: 'sports',
        label: 'Matchups',
        dest: '/matchups',
        key: 'matchups',
    },
    {
        icon: 'swap_horiz',
        label: 'Trades & Waivers',
        dest: '/transactions',
        key: 'transactions',
    },
    {
        icon: 'timeline',
        label: 'Timeline',
        dest: '/timeline',
        key: 'timeline',
    },
    {
        icon: 'article',
        label: 'Recaps',
        dest: '/recaps',
        key: 'recaps',
    },
    {
        icon: 'view_comfy',
        label: 'League Info',
        nest: true,
        key: 'league_info',
        children: [
            {
                icon: 'storage',
                label: 'Rosters',
                dest: '/rosters',
            },
            {
                icon: 'groups',
                label: 'Managers',
                dest: '/managers',
            },
            {
                icon: 'local_fire_department',
                label: 'Rivalries (all-time)',
                dest: '/rivalries',
            },
            {
                icon: 'compare_arrows',
                label: 'Head-to-Head Tool',
                dest: '/rivalry',
            },
            {
                icon: 'leaderboard',
                label: 'Standings',
                dest: '/standings',
            },
            {
                icon: 'shuffle',
                label: 'All-Play',
                dest: '/all-play',
            },
            {
                icon: 'tune',
                label: 'Lineup Efficiency',
                dest: '/efficiency',
            },
            {
                icon: 'auto_stories',
                label: 'All-Time Stats',
                dest: '/all-time',
            },
            {
                icon: 'menu_book',
                label: 'Record Book',
                dest: '/record-book',
            },
            {
                icon: 'percent',
                label: 'Playoff Odds',
                dest: '/odds',
            },
            {
                icon: 'visibility',
                label: 'Week Preview',
                dest: '/preview',
            },
            {
                icon: 'handshake',
                label: 'Trade Grades',
                dest: '/trade-grades',
            },
            {
                icon: 'grading',
                label: 'Draft Grades',
                dest: '/draft-grades',
            },
            {
                icon: 'casino',
                label: 'Luck Meter',
                dest: '/luck',
            },
            {
                icon: 'person_search',
                label: 'Player History',
                dest: '/players',
            },
            {
                icon: 'balance',
                label: 'Median & Schedule',
                dest: '/median',
            },
            {
                icon: 'shopping_cart',
                label: 'Waiver Returns',
                dest: '/waivers',
            },
            {
                icon: 'military_tech',
                label: 'Hall of Fame',
                dest: '/hall-of-fame',
            },
            {
                icon: 'view_comfy',
                label: 'Drafts',
                dest: '/drafts',
            },
            {
                icon: 'emoji_events',
                label: 'Trophy Room',
                dest: '/awards',
            },
            {
                icon: 'military_tech',
                label: 'Records',
                dest: '/records',
            },
            {
                icon: 'history_edu',
                label: 'League Rules',
                dest: '/rules',
            },
            {
                icon: 'sports_football',
                label: 'Go to Sleeper',
                dest: `https://sleeper.app/leagues/${leagueID}`,
            },
        ]
    },
    {
        icon: 'lightbulb',
        label: 'Resources',
        dest: '/resources',
        key: 'resources',
    },
];