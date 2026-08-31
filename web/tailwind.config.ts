import type { Config } from 'tailwindcss'
import { theme } from './src/theme/tokens'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'primary': theme.colors.primary,
        'primary-hover': theme.colors.primaryHover,
        'primary-light': theme.colors.primaryLight,
        'success': theme.colors.success,
        'warning': theme.colors.warning,
        'danger': theme.colors.danger,
        'purple': theme.colors.purple,
        'text': theme.colors.text,
        'bg': theme.colors.bg,
        'border': theme.colors.border,
        'grade': theme.colors.grade,
      },
      borderRadius: theme.radius,
    },
  },
  plugins: [],
}
export default config

