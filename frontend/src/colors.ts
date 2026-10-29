import { useEffect, useState } from 'react'

// Recharts writes colours into SVG attributes, where CSS variables do not
// resolve, so chart colours are plain values kept in step with index.css.
const light = {
  forecast: '#2563eb',
  actual: '#0f766e',
  over: '#d9480f',
  under: '#6741d9',
  muted: '#5d6b7c',
  highlight: 'rgba(37, 99, 235, 0.08)',
}

const dark: typeof light = {
  forecast: '#60a5fa',
  actual: '#2dd4bf',
  over: '#ff8a4c',
  under: '#a78bfa',
  muted: '#93a1b2',
  highlight: 'rgba(96, 165, 250, 0.12)',
}

export type Palette = typeof light

const query = '(prefers-color-scheme: dark)'

export function useColors(): Palette {
  const [isDark, setDark] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = (e: MediaQueryListEvent) => setDark(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return isDark ? dark : light
}
