/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F7F8F6',
        ink: { DEFAULT: '#1C2A33', soft: '#4A5963', faint: '#7A8790' },
        rule: '#D9DED9',
        verified: { DEFAULT: '#0E7C66', tint: '#E3F1EC' },
        pending: { DEFAULT: '#B86E00', tint: '#FBF0DF' },
        blocked: { DEFAULT: '#B3261E', tint: '#F9E5E3' },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        serif: ['"IBM Plex Serif"', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
