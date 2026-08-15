/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#f5f6f2',
        panel: '#ffffff',
        hairline: {
          DEFAULT: '#e2e4dd',
          strong: '#cdd0c6',
        },
        ink: {
          900: '#14171b',
          700: '#363b35',
          500: '#6b7167',
          400: '#8b9086',
          300: '#c8cbc2',
        },
        brand: {
          DEFAULT: '#3730a3',
          soft: '#ecebfa',
        },
        up: {
          DEFAULT: '#0f7b3f',
          soft: '#e6f5ea',
        },
        down: {
          DEFAULT: '#b91c1c',
          soft: '#fbe9e9',
        },
        amber: {
          DEFAULT: '#b45309',
          soft: '#fbf0da',
        },
        sym: {
          gold: '#a3690a',
          silver: '#5b6169',
          nasdaq: '#3730a3',
          us30: '#0f7b3f',
          eur: '#0e7490',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        body: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui'],
      },
    },
  },
  plugins: [],
}
