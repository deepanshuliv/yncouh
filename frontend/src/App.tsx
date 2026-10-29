import { useEffect, useState } from 'react'
import { api, type Day, type Horizon, type Meta, type Summary } from './api'
import { AnalysisTabs } from './components/Charts'
import { DayView } from './components/DayView'
import { Insights } from './components/Insights'
import { Kpis } from './components/Kpis'
import { cutoffOptions } from './format'

const PRESET_NAMES: Record<string, string> = { '09:20': 'EPEX', '09:50': 'N2EX' }

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [cutoff, setCutoff] = useState<string | null>(null)
  const [date, setDate] = useState<string | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [horizon, setHorizon] = useState<Horizon | null>(null)
  const [day, setDay] = useState<Day | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .meta()
      .then((m) => {
        setMeta(m)
        setCutoff(m.defaultCutoff)
        setDate(m.firstDeliveryDay)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!cutoff) return
    Promise.all([api.summary(cutoff), api.horizon(cutoff)])
      .then(([s, h]) => {
        setSummary(s)
        setHorizon(h)
      })
      .catch((e: Error) => setError(e.message))
  }, [cutoff])

  useEffect(() => {
    if (!cutoff || !date) return
    api.day(date, cutoff).then(setDay).catch((e: Error) => setError(e.message))
  }, [cutoff, date])

  if (error) return <div className="page status">Could not load data: {error}</div>
  if (!meta || !cutoff || !date) return <div className="page status">Loading…</div>

  const isPreset = meta.cutoffPresets.some((p) => p.time === cutoff)

  return (
    <div className="page">
      <header className="top">
        <div>
          <h1>Wind Forecast Monitor</h1>
          <p>GB national wind · day-ahead decisions · January 2026</p>
        </div>
        <div className="cutoff">
          <span className="cutoff-label">Bid deadline (day before)</span>
          <div className="segmented">
            {meta.cutoffPresets.map((p) => (
              <button key={p.time} className={p.time === cutoff ? 'on' : ''} onClick={() => setCutoff(p.time)} title={p.label}>
                {PRESET_NAMES[p.time] ?? p.label} {p.time}
              </button>
            ))}
            <select
              className={isPreset ? '' : 'on'}
              value={isPreset ? '' : cutoff}
              onChange={(e) => e.target.value && setCutoff(e.target.value)}
              aria-label="Other decision time"
            >
              <option value="">Other</option>
              {cutoffOptions.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {summary && horizon ? (
        <main className="stack">
          <Kpis summary={summary} />
          <DayView day={day} date={date} first={meta.firstDeliveryDay} last={meta.lastDeliveryDay} onDate={setDate} />
          <Insights summary={summary} horizon={horizon} />
          <AnalysisTabs summary={summary} horizon={horizon} selected={date} onSelect={setDate} />
        </main>
      ) : (
        <div className="status">Loading analysis…</div>
      )}

      <footer>
        Source: Elexon BMRS (WINDFOR, FUELHH) · uses only forecasts published before the deadline · error = forecast −
        actual
      </footer>
    </div>
  )
}
