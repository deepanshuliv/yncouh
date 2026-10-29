import type { Horizon, Summary } from '../api'
import { power, ukDayMonth } from '../format'

/** Three short takeaways for the trading desk, derived from the numbers. */
export function Insights({ summary, horizon }: { summary: Summary; horizon: Horizon }) {
  const m = summary.overall
  if (!m.count || m.bias == null) return null

  const worst = [...summary.daily].sort((a, b) => (b.mae ?? 0) - (a.mae ?? 0)).slice(0, 3)
  const peak = [...summary.byTimeOfDay].sort((a, b) => (b.mae ?? 0) - (a.mae ?? 0))[0]
  const nearest = horizon.buckets[0]
  const used = horizon.decisionHorizon

  return (
    <section className="card">
      <h2>Takeaways</h2>
      <ul className="takeaways">
        <li>
          <b>Systematic, so correctable.</b> Even 0–3 h ahead the forecast is {power(nearest?.bias, true)} high. Likely
          curtailment, not weather.
        </li>
        {used && (
          <li>
            <b>Older forecast, bigger miss.</b> Day-ahead bids rely on forecasts {Math.round(used.min)}–
            {Math.round(used.max)} h old. Leave some volume for intraday.
          </li>
        )}
        {peak && (
          <li>
            <b>Watch {peak.slot}.</b> The hardest time of day. Worst days:{' '}
            {worst.map((d) => ukDayMonth(`${d.date}T12:00:00Z`)).join(', ')}.
          </li>
        )}
      </ul>
    </section>
  )
}
