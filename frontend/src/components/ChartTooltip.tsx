import { power } from '../format'

interface Entry {
  name?: string
  value?: number
  color?: string
}

interface Props {
  active?: boolean
  label?: string | number
  payload?: Entry[]
  title?: (label: string | number) => string
}

/** Shared tooltip: every series is a power value. */
export function ChartTooltip({ active, label, payload, title }: Props) {
  if (!active || !payload?.length || label == null) return null
  return (
    <div className="tooltip">
      <div className="t">{title ? title(label) : label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: {power(p.value, p.name?.toLowerCase().includes('bias') || p.name === 'Error')}
        </div>
      ))}
    </div>
  )
}
