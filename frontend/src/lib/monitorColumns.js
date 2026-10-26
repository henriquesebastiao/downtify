// Layout preferences only: never hide the identity or row actions.
export const MONITOR_COLUMNS = [
  { key: 'name', width: 320, min: 240, max: 900 },
  { key: 'source', width: 140, min: 110, max: 300, label: 'monitor.colSource' },
  { key: 'checks', width: 190, min: 160, max: 360, label: 'monitor.colChecks' },
  {
    key: 'checked',
    width: 180,
    min: 150,
    max: 360,
    label: 'monitor.colLastChecked',
  },
  { key: 'size', width: 110, min: 90, max: 240, label: 'monitor.colSize' },
  { key: 'active', width: 80, min: 64, max: 160, label: 'monitor.colActive' },
  { key: 'actions', width: 128, min: 128, max: 240, label: 'common.more' },
]

export function monitorLayout(value) {
  const widths = Object.fromEntries(
    MONITOR_COLUMNS.map((col) => {
      const width = value?.widths?.[col.key]
      return [
        col.key,
        typeof width === 'number' && Number.isFinite(width)
          ? Math.min(col.max, Math.max(col.min, Math.round(width)))
          : col.width,
      ]
    })
  )
  const optional = new Set(MONITOR_COLUMNS.slice(1, -1).map((col) => col.key))
  const hidden = Array.isArray(value?.hidden)
    ? [...new Set(value.hidden.filter((key) => optional.has(key)))]
    : []
  return { widths, hidden }
}

export function resizeMonitorColumn(value, key, width) {
  const layout = monitorLayout(value)
  if (MONITOR_COLUMNS.some((col) => col.key === key)) layout.widths[key] = width
  return monitorLayout(layout)
}

export function toggleMonitorColumn(value, key) {
  const layout = monitorLayout(value)
  layout.hidden = layout.hidden.includes(key)
    ? layout.hidden.filter((item) => item !== key)
    : [...layout.hidden, key]
  return monitorLayout(layout)
}
