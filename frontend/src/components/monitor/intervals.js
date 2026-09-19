// Check intervals offered for a watch, with their labels.
export const WATCH_INTERVALS = [
  15, 30, 60, 180, 360, 720, 1440, 10080, 20160, 43200,
]

export function intervalLabel(t, minutes) {
  if (minutes < 60) return t('monitor.everyMinutes', { count: minutes })
  if (minutes < 1440) return t('monitor.everyHours', { count: minutes / 60 })
  if (minutes < 10080) return t('monitor.everyDays', { count: minutes / 1440 })
  if (minutes < 43200)
    return t('monitor.everyWeeks', { count: minutes / 10080 })
  return t('monitor.everyMonths', { count: Math.round(minutes / 43200) })
}

/** Select options; keeps a stored value that isn't in the list. */
export function intervalOptions(t, current) {
  const values =
    WATCH_INTERVALS.includes(current) || !current
      ? WATCH_INTERVALS
      : [...WATCH_INTERVALS, current].sort((a, b) => a - b)
  return values.map((value) => ({ value, label: intervalLabel(t, value) }))
}
