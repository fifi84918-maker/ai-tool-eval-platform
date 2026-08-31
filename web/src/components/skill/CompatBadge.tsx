/**
 * CompatBadge — renders a coloured badge for the 7-state compat_status.
 *
 * Colour map (§6.3):
 *   COMPATIBLE              → green  #22c55e
 *   COMPATIBLE_WITH_ADAPTER → lime   #84cc16
 *   PENDING_VERIFICATION    → yellow #eab308
 *   PARTIAL                 → orange #f97316
 *   UNKNOWN                 → grey   #6b7280
 *   INCOMPATIBLE            → red    #ef4444
 *   BLOCKED                 → red    #dc2626 (darker, with lock icon)
 */

interface CompatBadgeProps {
  status: string | null | undefined
  size?: 'sm' | 'md'
}

const COMPAT_META: Record<string, { label: string; bg: string; text: string; icon?: string }> = {
  COMPATIBLE:              { label: 'Compatible',       bg: '#22c55e', text: '#fff' },
  COMPATIBLE_WITH_ADAPTER: { label: 'Needs Adapter',   bg: '#84cc16', text: '#fff' },
  PENDING_VERIFICATION:    { label: 'Pending Verify',  bg: '#eab308', text: '#fff' },
  PARTIAL:                 { label: 'Partial',         bg: '#f97316', text: '#fff' },
  UNKNOWN:                 { label: 'Unknown',         bg: '#6b7280', text: '#fff' },
  INCOMPATIBLE:            { label: 'Incompatible',    bg: '#ef4444', text: '#fff' },
  BLOCKED:                 { label: 'Blocked',         bg: '#dc2626', text: '#fff', icon: '🔒' },
}

export default function CompatBadge({ status, size = 'md' }: CompatBadgeProps) {
  const meta = COMPAT_META[status ?? 'UNKNOWN'] ?? COMPAT_META['UNKNOWN']
  const pad  = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-full ${pad}`}
      style={{ backgroundColor: meta.bg, color: meta.text }}
      title={`Compat status: ${status ?? 'UNKNOWN'}`}
    >
      {meta.icon && <span>{meta.icon}</span>}
      {meta.label}
    </span>
  )
}
