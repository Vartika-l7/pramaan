/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: '#FBF8F3', subtle: '#F4EFE6' },
        ivory: { DEFAULT: '#FBF8F3', dark: '#F4EFE6' },
        surface: { DEFAULT: '#FBF8F3', raised: '#FFFFFF' },
        panel: '#FFFFFF',
        ink: { DEFAULT: '#2B1B17', secondary: '#7A5C52', tertiary: '#7A5C52', muted: '#7A5C52' },
        muted: '#7A5C52',
        border: { DEFAULT: '#E8D9CC', strong: '#D3BEAE' },
        vermilion: { DEFAULT: '#DB4A2B', dark: '#B83A1F', light: '#FDF0EC' },
        teal: { DEFAULT: '#2E5E6E', light: '#EDF4F6', border: '#B8D0D8' },
        amber: { DEFAULT: '#C97B1A', light: '#FCF4E8', border: '#E8C99B' },
        approved: { DEFAULT: '#3F7D58', light: '#EEF6F1', border: '#B4D4C0' },
        /* Compatibility aliases mapped strictly to the new tokens */
        cobalt: { DEFAULT: '#2E5E6E', light: '#EDF4F6', dark: '#234955' },
        tomato: { DEFAULT: '#DB4A2B', light: '#FDF0EC', dark: '#B83A1F' },
        ochre: { DEFAULT: '#C97B1A', light: '#FCF4E8', dark: '#C97B1A' },
        lime: { DEFAULT: '#3F7D58', light: '#EEF6F1', dark: '#3F7D58' },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '6px',
        lg: '6px',
        xl: '6px',
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
    },
  },
  plugins: [],
};
