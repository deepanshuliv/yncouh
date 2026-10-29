import type { Summary } from '../api'
import { power } from '../format'

export function Kpis({ summary }: { summary: Summary }) {
  const m = summary.overall
  const over = (m.bias ?? 0) > 0
  const items = [
    { label: 'Typical miss', value: power(m.mae), hint: `${m.nmae_pct?.toFixed(0)}% of avg output` },
    { label: 'Bias', value: power(m.bias, true), hint: over ? 'Forecast too high' : 'Forecast too low', tone: over ? 'over' : 'under' },
    { label: 'Miss after bias fix', value: power(m.error_std), hint: 'Correctable part removed' },
    { label: '90% reserve', value: power(m.shortfall_p90), hint: `${power(m.shortfall_p90_debiased)} after bias fix` },
  ]
  return (
    <section className="kpis">
      {items.map((k) => (
        <div className="kpi" key={k.label}>
          <div className="label">{k.label}</div>
          <div className={`value ${k.tone ?? ''}`}>{k.value}</div>
          <div className="hint">{k.hint}</div>
        </div>
      ))}
    </section>
  )
}
