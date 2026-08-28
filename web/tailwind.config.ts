import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#165DFF',
        'primary-hover': '#4080FF',
        'primary-light': 'rgba(22, 93, 255, 0.08)',
        'text': {
          'primary': '#1D2129',
          'secondary': '#4E5969',
          'tertiary': '#86909C',
        },
        'bg': {
          'page': '#FFFFFF',
          'card': '#F5F7FA',
        },
        'border': '#E5E6EB',
        'grade': {
          'a': '#00B42A',
          'b': '#165DFF',
          'c': '#FF7D00',
          'd': '#F53F3F',
          'u': '#86909C',
        },
      },
    },
  },
  plugins: [],
}
export default config

