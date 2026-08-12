/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#07070b',
          900: '#0c0c14',
          850: '#111120',
          800: '#161629',
          700: '#20203a',
          600: '#2c2c4d',
        },
        signal: {
          violet: '#7c6cf0',
          indigo: '#5b4fe0',
          amber: '#f0b040',
          green: '#3ecf8e',
          red: '#f0555c',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        body: ['"Inter"', 'ui-sans-serif', 'system-ui'],
      },
      backgroundImage: {
        'grid-fade':
          'linear-gradient(to bottom, rgba(124,108,240,0.06), transparent 60%)',
      },
    },
  },
  plugins: [],
}
