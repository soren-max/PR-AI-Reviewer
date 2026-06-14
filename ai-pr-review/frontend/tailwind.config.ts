import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        // Severity colors
        'severity-critical': '#dc2626',
        'severity-major': '#ea580c',
        'severity-minor': '#ca8a04',
        'severity-info': '#6b7280',
        // Score gauge colors
        'score-excellent': '#16a34a',
        'score-good': '#ca8a04',
        'score-fair': '#ea580c',
        'score-poor': '#dc2626',
      },
      animation: {
        'gauge-fill': 'gauge-fill 1s ease-out forwards',
      },
      keyframes: {
        'gauge-fill': {
          '0%': { strokeDashoffset: '283' },
          '100%': { strokeDashoffset: 'var(--target-offset)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
