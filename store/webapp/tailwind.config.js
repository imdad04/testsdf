/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a1a',
        card: '#15152b',
        cardSoft: '#1f1f3a',
        accent: '#7c5cff',
        accentSoft: '#5a3dff',
        muted: '#8a8aa3',
      },
      boxShadow: {
        glow: '0 0 30px rgba(124, 92, 255, 0.25)',
      },
    },
  },
  plugins: [],
};
