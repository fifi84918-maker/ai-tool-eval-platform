/**
 * Design System - Theme Tokens
 * Central source of truth for colors, spacing, and other design values
 */

export const theme = {
  colors: {
    // Primary brand color
    primary: '#165DFF',
    primaryHover: '#4080FF',
    primaryLight: 'rgba(22, 93, 255, 0.08)',
    
    // Text colors
    text: {
      primary: '#1D2129',
      secondary: '#4E5969',
      tertiary: '#86909C',
    },
    
    // Background colors
    bg: {
      page: '#FFFFFF',
      card: '#F5F7FA',
    },
    
    // Border color
    border: '#E5E6EB',
    
    // Semantic colors - Success/Warning/Danger
    success: '#00B42A',
    warning: '#FF7D00',
    danger: '#F53F3F',
    purple: '#722ED1',
    
    // Grade colors (matching skill evaluation system)
    grade: {
      a: '#00B42A',  // Green - Excellent
      b: '#165DFF',  // Blue - Good
      c: '#FF7D00',  // Orange - Acceptable
      d: '#F53F3F',  // Red - Poor
      u: '#86909C',  // Gray - Unknown
    },
  },
  
  // Spacing scale (can be extended)
  spacing: {
    xs: '0.25rem',   // 4px
    sm: '0.5rem',    // 8px
    md: '1rem',      // 16px
    lg: '1.5rem',    // 24px
    xl: '2rem',      // 32px
    '2xl': '3rem',   // 48px
  },
  
  // Border radius
  radius: {
    sm: '0.375rem',   // 6px
    md: '0.5rem',     // 8px
    lg: '0.75rem',    // 12px
    xl: '1rem',       // 16px
    '2xl': '1.5rem',  // 24px
    full: '9999px',
  },
} as const

export type Theme = typeof theme
