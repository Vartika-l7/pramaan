/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ivory: { DEFAULT: '#F4F0E7', dark: '#EAE6DC' },
        surface: { DEFAULT: '#FBF9F4', raised: '#FFFFFF' },
        ink: { DEFAULT: '#252A32', secondary: '#77766F', tertiary: '#A09E97', muted: '#77766F', light: '#A09E97' },
        border: { DEFAULT: '#DDD9CF', strong: '#C4BFB4' },
        cobalt: { DEFAULT: '#315FCE', light: '#EEF2FC', dark: '#1E3D8A' },
        tomato: { DEFAULT: '#F05A3A', light: '#FEF0EC', dark: '#B53920' },
        lime: { DEFAULT: '#D6E36A', light: '#F5F9DC', dark: '#8FA820' },
        lavender: { DEFAULT: '#B9A4D8', light: '#F3F0FB', dark: '#6B4FA8' },
        ochre: { DEFAULT: '#E7B75B', light: '#FDF5E4', dark: '#A07820' },

        /* Safety fallbacks mapping legacy tokens to light editorial palette */
        paper: {
          DEFAULT: '#F4F0E7',
          dark: '#EAE6DC',
          panel: '#FBF9F4',
          border: '#DDD9CF',
        },
        vermilion: {
          DEFAULT: '#F05A3A',
          hover: '#B53920',
          light: '#FEF0EC',
        },
      },
      fontFamily: {
        serif: ['"Fraunces"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '3px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
    },
  },
  plugins: [],
}
