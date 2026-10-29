import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Day } from '../api'
import { useColors } from '../colors'
import { gwTick, power, shiftDate, ukDateTime, ukLongDay, ukTime } from '../format'
import { ChartTooltip } from './ChartTooltip'

interface Props {
  day: Day | null
  date: string
  first: string
  last: string
  onDate: (date: string) => void
}

export function DayView({ day, date, first, last, onDate }: Props) {
  const c = useColors()
  const m = day?.metrics
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>{ukLongDay(date)}</h2>
          {day && m && (
            <p className="meta">
              Forecast from {ukDateTime(day.forecastRuns[0] ?? day.decisionTime)} · miss <b>{power(m.mae)}</b> · bias{' '}
              <b className={(m.bias ?? 0) > 0 ? 'over' : 'under'}>{power(m.bias, true)}</b>
            </p>
          )}
        </div>
        <div className="day-nav">
          <button onClick={() => onDate(shiftDate(date, -1))} disabled={date <= first} aria-label="Previous day">
            ‹
          </button>
          <input type="date" value={date} min={first} max={last} onChange={(e) => e.target.value && onDate(e.target.value)} />
          <button onClick={() => onDate(shiftDate(date, 1))} disabled={date >= last} aria-label="Next day">
            ›
          </button>
        </div>
      </div>

      <div className="legend">
        <span>
          <i style={{ background: c.actual }} /> Actual
        </span>
        <span>
          <i className="dashed" style={{ borderColor: c.forecast }} /> Forecast at decision time
        </span>
      </div>

      <div className="chart tall">
        {day && (
          <ResponsiveContainer>
            <LineChart data={day.points} margin={{ top: 12, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="time" tickFormatter={ukTime} interval={7} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={(v: number) => `${gwTick(v)} GW`} tickLine={false} axisLine={false} width={56} />
              <Tooltip content={<ChartTooltip title={(t) => ukTime(String(t))} />} />
              <Line isAnimationActive={false} dataKey="actual" name="Actual" stroke={c.actual} strokeWidth={2.5} dot={false} />
              <Line
                isAnimationActive={false}
                dataKey="forecast"
                name="Forecast"
                stroke={c.forecast}
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  )
}
