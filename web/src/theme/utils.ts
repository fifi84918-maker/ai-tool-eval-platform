/**
 * Theme utility functions
 */

import { theme } from './tokens'

/**
 * Get grade color from theme
 */
export function getGradeColor(grade: string | null | undefined): string {
  if (!grade) return theme.colors.grade.u
  
  const gradeKey = grade.toLowerCase() as 'a' | 'b' | 'c' | 'd' | 'u'
  return theme.colors.grade[gradeKey] || theme.colors.grade.u
}

/**
 * Get grade Tailwind class
 */
export function getGradeClass(grade: string | null | undefined): string {
  if (!grade) return 'bg-grade-u'
  
  const gradeUpper = grade.toUpperCase()
  const classMap: Record<string, string> = {
    'A': 'bg-grade-a',
    'B': 'bg-grade-b',
    'C': 'bg-grade-c',
    'D': 'bg-grade-d',
    'U': 'bg-grade-u',
  }
  
  return classMap[gradeUpper] || 'bg-grade-u'
}

/**
 * Get severity color (for findings/alerts)
 */
export function getSeverityColor(severity: string): string {
  const severityMap: Record<string, string> = {
    'critical': theme.colors.danger,
    'high': theme.colors.danger,
    'medium': theme.colors.warning,
    'low': theme.colors.text.tertiary,
    'info': theme.colors.text.tertiary,
  }
  
  return severityMap[severity.toLowerCase()] || theme.colors.text.tertiary
}
