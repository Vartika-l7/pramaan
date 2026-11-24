/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        /* Warm Pearl & Neutral Surfaces */
        paper: { DEFAULT: '#F5F4F0', subtle: '#ECEAE3' },
        ivory: { DEFAULT: '#F5F4F0', dark: '#ECEAE3' },
        surface: { DEFAULT: '#F5F4F0', raised: '#FFFFFF' },
        panel: '#FFFFFF',

        /* Midnight Ink Anchor Surface (#20283A) */
        obsidian: { DEFAULT: '#20283A', elevated: '#2B364E', muted: '#364360' },

        /* High-Contrast Ink & Slate Secondary Text */
        ink: { DEFAULT: '#20283A', secondary: '#455066', tertiary: '#5E6A82', muted: '#556077' },
        muted: '#556077',

        /* Architectural Stone Hairline Borders */
        border: { DEFAULT: '#E1DFD7', strong: '#C9C6BC' },

        /* Primary Brand & Action Accent: Deep Teal (#316A78) */
        teal: { DEFAULT: '#316A78', dark: '#24525D', light: '#EAF2F4', border: '#B2CDD4' },

        /* Secondary Interactive Accent: Slate Blue (#5576A5) */
        slate: { DEFAULT: '#5576A5', dark: '#415E87', light: '#EEF2F8', border: '#C1CFE4' },
        violet: { DEFAULT: '#5576A5', dark: '#415E87', light: '#EEF2F8', border: '#C1CFE4' },

        /* Warning / Medium Severity Accent: Muted Amber (#D59A45, AA text #8F6018) */
        amber: { DEFAULT: '#9A6819', fill: '#D59A45', dark: '#7D5312', light: '#FCF5E7', border: '#E8CFA0' },

        /* Critical Integrity Alerts: Alert Coral (#D95749, AA text #B83A2D) */
        vermilion: { DEFAULT: '#C74437', fill: '#D95749', dark: '#A63327', light: '#FDF0EE' },

        /* Human-Approved Admissibility: Forest Emerald */
        approved: { DEFAULT: '#246B4F', light: '#ECF6F1', border: '#B2D9C7' },

        /* Compatibility aliases */
        cobalt: { DEFAULT: '#316A78', light: '#EAF2F4', dark: '#24525D' },
        tomato: { DEFAULT: '#C74437', light: '#FDF0EE', dark: '#A63327' },
        ochre: { DEFAULT: '#9A6819', light: '#FCF5E7', dark: '#7D5312' },
        lime: { DEFAULT: '#246B4F', light: '#ECF6F1', dark: '#246B4F' },
      },
      fontFamily: {
        serif: ['"DM Serif Display"', '"Source Serif 4"', 'Georgia', 'serif'],
        editorial: ['"DM Serif Display"', '"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', '"IBM Plex Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        sm: '5px',
        DEFAULT: '8px',
        md: '8px',
        lg: '12px',
        xl: '14px',
        '2xl': '16px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(32, 40, 58, 0.04), 0 6px 18px -12px rgba(32, 40, 58, 0.10)',
        'card-hover': '0 2px 6px rgba(32, 40, 58, 0.06), 0 12px 24px -12px rgba(32, 40, 58, 0.14)',
        popover: '0 10px 28px -6px rgba(32, 40, 58, 0.16), 0 2px 6px rgba(32, 40, 58, 0.06)',
        obsidian: '0 14px 34px -14px rgba(32, 40, 58, 0.38)',
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
    },
  },
  plugins: [],
};
