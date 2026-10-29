import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Horizon, Summary } from '../api'
import { useColors, type Palette } from '../colors'
import { gwTick, power, ukLongDay } from '../format'
import { ChartTooltip } from './ChartTooltip'

const MARGIN = { top: 12, right: 8, bottom: 0, left: 0 }
const AXIS = { tickLine: false, axisLine: false } as const
const GW_AXIS = { ...AXIS, tickFormatter: (v: number) => `${gwTick(v)} GW`, width: 56 }

type Tab = 'day' | 'horizon' | 'time' | 'spread'

const TABS: { id: Tab; label: string; caption: string }[] = [
  { id: 'day', label: 'By day', caption: 'Typical miss per delivery day. Click a bar to open that day.' },
  { id: 'horizon', label: 'By lead time', caption: 'Error grows the further ahead a forecast is made. Shaded: what day-ahead bids use.' },
  { id: 'time', label: 'By time of day', caption: 'Typical miss for each half-hour of the day (UK time).' },
  { id: 'spread', label: 'Error spread', caption: 'How often each size of error (GW) happened. Right of zero: forecast too high.' },
]

interface Props {
  summary: Summary
  horizon: Horizon
  selected: string
  onSelect: (date: string) => void
}

export function AnalysisTabs({ summary, horizon, selected, onSelect }: Props) {
  const c = useColors()
  // The open tab follows the URL hash (#horizon etc.) so each view can be linked.
  const [tab, setTabState] = useState<Tab>(() => TABS.find((t) => `#${t.id}` === window.location.hash)?.id ?? 'day')
  const setTab = (t: Tab) => {
    setTabState(t)
    window.history.replaceState(null, '', `#${t}`)
  }
  const current = TABS.find((t) => t.id === tab)!

  return (
    <section className="card">
      <div className="card-head">
        <h2>January breakdown</h2>
        <div className="segmented" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={t.id === tab} className={t.id === tab ? 'on' : ''} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <p className="meta">{current.caption}</p>
      <div className="legend">
        {tab === 'spread' ? (
          <>
            <span>
              <i style={{ background: c.over }} /> Forecast too high
            </span>
            <span>
              <i style={{ background: c.under }} /> Forecast too low
            </span>
          </>
        ) : (
          <>
            <span>
              <i style={{ background: c.actual }} /> Typical miss (MAE)
            </span>
            <span>
              <i style={{ background: c.over }} /> Bias
            </span>
          </>
        )}
      </div>
      <div className="chart">
        {tab === 'day' ? (
            <DailyChart summary={summary} selected={selected} onSelect={onSelect} c={c} />
          ) : tab === 'horizon' ? (
            <HorizonChart horizon={horizon} c={c} />
          ) : tab === 'time' ? (
            <TimeOfDayChart summary={summary} c={c} />
          ) : (
            <HistogramChart summary={summary} c={c} />
          )}
      </div>
    </section>
  )
}

function DailyChart({ summary, selected, onSelect, c }: Omit<Props, 'horizon'> & { c: Palette }) {
  return (
    <ResponsiveContainer>
    <ComposedChart
      data={summary.daily}
      margin={MARGIN}
      onClick={(e) => e?.activeLabel && onSelect(String(e.activeLabel))}
      style={{ cursor: 'pointer' }}
    >
      <CartesianGrid vertical={false} />
      <XAxis dataKey="date" tickFormatter={(d: string) => String(Number(d.slice(8)))} interval={2} {...AXIS} />
      <YAxis {...GW_AXIS} />
      <Tooltip content={<ChartTooltip title={(d) => ukLongDay(String(d))} />} />
      <ReferenceLine y={0} stroke={c.muted} />
      <Bar isAnimationActive={false} dataKey="mae" name="MAE" radius={[3, 3, 0, 0]}>
        {summary.daily.map((d) => (
          <Cell key={d.date} fill={d.date === selected ? c.forecast : c.actual} opacity={d.date === selected ? 1 : 0.6} />
        ))}
      </Bar>
      <Line isAnimationActive={false} dataKey="bias" name="Bias" stroke={c.over} strokeWidth={2} dot={false} />
    </ComposedChart>
    </ResponsiveContainer>
  )
}

function HorizonChart({ horizon, c }: { horizon: Horizon; c: Palette }) {
  const used = horizon.decisionHorizon
  return (
    <ResponsiveContainer>
    <ComposedChart data={horizon.buckets} margin={MARGIN}>
      <CartesianGrid vertical={false} />
      <XAxis
        dataKey="fromHours"
        type="number"
        domain={[0, 42]}
        ticks={[0, 6, 12, 18, 24, 30, 36, 42]}
        tickFormatter={(h: number) => `${h} h`}
        {...AXIS}
      />
      <YAxis {...GW_AXIS} domain={[0, 'auto']} />
      <Tooltip content={<ChartTooltip title={(h) => `${h}–${Number(h) + 3} h ahead`} />} />
      {used && <ReferenceArea x1={Math.floor(used.min / 3) * 3} x2={Math.floor(used.max / 3) * 3} fill={c.highlight} />}
      <Line isAnimationActive={false} dataKey="mae" name="MAE" stroke={c.actual} strokeWidth={2.5} dot={false} />
      <Line isAnimationActive={false} dataKey="bias" name="Bias" stroke={c.over} strokeWidth={2} dot={false} />
    </ComposedChart>
    </ResponsiveContainer>
  )
}

function TimeOfDayChart({ summary, c }: { summary: Summary; c: Palette }) {
  return (
    <ResponsiveContainer>
    <ComposedChart data={summary.byTimeOfDay} margin={MARGIN}>
      <CartesianGrid vertical={false} />
      <XAxis dataKey="slot" interval={5} {...AXIS} />
      <YAxis {...GW_AXIS} />
      <Tooltip content={<ChartTooltip title={(s) => String(s)} />} />
      <Bar isAnimationActive={false} dataKey="mae" name="MAE" fill={c.actual} opacity={0.6} radius={[2, 2, 0, 0]} />
      <Line isAnimationActive={false} dataKey="bias" name="Bias" stroke={c.over} strokeWidth={2} dot={false} />
    </ComposedChart>
    </ResponsiveContainer>
  )
}

function HistogramChart({ summary, c }: { summary: Summary; c: Palette }) {
  const data = summary.histogram.map((b) => ({ ...b, mid: (b.from + b.to) / 2 }))
  return (
    <ResponsiveContainer>
    <BarChart data={data} margin={MARGIN} barCategoryGap={1}>
      <CartesianGrid vertical={false} />
      <XAxis dataKey="from" tickFormatter={gwTick} interval="preserveStartEnd" minTickGap={12} {...AXIS} />
      <YAxis allowDecimals={false} {...AXIS} width={56} />
      <Tooltip
        content={({ active, payload }) => {
          const b = payload?.[0]?.payload as (typeof data)[number] | undefined
          if (!active || !b) return null
          return (
            <div className="tooltip">
              <div className="t">
                {power(b.from, true)} to {power(b.to, true)}
              </div>
              {b.count} half-hours
            </div>
          )
        }}
      />
      <ReferenceLine x={0} stroke={c.muted} />
      <Bar isAnimationActive={false} dataKey="count" name="Half-hours" radius={[2, 2, 0, 0]}>
        {data.map((b) => (
          <Cell key={b.from} fill={b.mid > 0 ? c.over : c.under} opacity={0.8} />
        ))}
      </Bar>
    </BarChart>
    </ResponsiveContainer>
  )
}
