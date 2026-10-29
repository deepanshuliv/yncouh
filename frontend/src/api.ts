export interface Metrics {
  count: number
  mae: number | null
  rmse: number | null
  bias: number | null
  error_std: number | null
  nmae_pct: number | null
  max_abs_error: number | null
  p90_abs_error: number | null
  shortfall_p90: number | null
  shortfall_p90_debiased: number | null
}

export interface Meta {
  firstDeliveryDay: string
  lastDeliveryDay: string
  defaultCutoff: string
  cutoffPresets: { time: string; label: string }[]
  alignment: string
  forecastRunTimes: string[]
}

export interface DayPoint {
  time: string
  forecast: number
  actual: number
  error: number
  horizonHours: number
}

export interface Day {
  date: string
  decisionTime: string
  forecastRuns: string[]
  metrics: Metrics
  points: DayPoint[]
}

export interface Summary {
  cutoff: string
  overall: Metrics
  meanActual: number | null
  daily: (Metrics & { date: string })[]
  byTimeOfDay: (Metrics & { slot: string })[]
  histogram: { from: number; to: number; count: number }[]
}

export interface Horizon {
  buckets: (Metrics & { fromHours: number; toHours: number })[]
  decisionHorizon: { min: number; max: number } | null
}

async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const query = new URLSearchParams(params).toString()
  const res = await fetch(`/api/${path}${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`${path}: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  meta: () => get<Meta>('meta'),
  summary: (cutoff: string) => get<Summary>('summary', { cutoff }),
  horizon: (cutoff: string) => get<Horizon>('horizon', { cutoff }),
  day: (date: string, cutoff: string) => get<Day>('day', { date, cutoff }),
}
