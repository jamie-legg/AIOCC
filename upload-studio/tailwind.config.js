/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
      },
      colors: {
        studio: {
          bg: '#070c12',
          panel: '#101720',
          panelSoft: '#131c27',
          border: '#213041',
          text: '#eef6ff',
          muted: '#91a1b5',
          cyan: '#32c7f4',
          cyanSoft: '#173244',
          green: '#39d98a',
          danger: '#ff355d',
        },
      },
      boxShadow: {
        glow: '0 0 28px rgba(50, 199, 244, 0.18)',
        panel: '0 18px 60px rgba(0, 0, 0, 0.35)',
      },
    },
  },
  plugins: [],
};
