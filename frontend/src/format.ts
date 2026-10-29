const UK = 'Europe/London'

const clock = new Intl.DateTimeFormat('en-GB', { timeZone: UK, hour: '2-digit', minute: '2-digit' })
const dayMonth = new Intl.DateTimeFormat('en-GB', { timeZone: UK, day: 'numeric', month: 'short' })
const longDay = new Intl.DateTimeFormat('en-GB', {
  timeZone: UK,
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

export const ukTime = (iso: string) => clock.format(new Date(iso))
export const ukDayMonth = (iso: string) => dayMonth.format(new Date(iso))
export const ukLongDay = (isoDate: string) => longDay.format(new Date(`${isoDate}T12:00:00Z`))
export const ukDateTime = (iso: string) => `${ukDayMonth(iso)} ${ukTime(iso)}`

/** 11284 -> "11.3 GW"; 940 -> "940 MW". */
export function power(mw: number | null | undefined, signed = false): string {
  if (mw == null || Number.isNaN(mw)) return '–'
  const sign = signed && mw > 0 ? '+' : mw < 0 ? '−' : ''
  const abs = Math.abs(mw)
  return abs >= 1000 ? `${sign}${(abs / 1000).toFixed(2)} GW` : `${sign}${Math.round(abs)} MW`
}

export const gwTick = (mw: number) => `${Number((mw / 1000).toFixed(1))}`
export const pct = (v: number | null | undefined) => (v == null ? '–' : `${v.toFixed(1)}%`)

export function shiftDate(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export const cutoffOptions = Array.from({ length: 48 }, (_, i) => {
  const h = String(Math.floor(i / 2)).padStart(2, '0')
  return `${h}:${i % 2 ? '30' : '00'}`
})
