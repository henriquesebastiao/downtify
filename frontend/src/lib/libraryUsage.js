// Library storage and usage helpers (GET /api/library/usage and
// /api/library/usage/scan): the growth chart's geometry and the rows the
// page lists. Pure functions - the page fetches.

/** The periods the page can cover, in days. */
export const USAGE_PERIODS = [7, 30, 90, 365]

/** The download outcomes, in the order the page shows them. */
export const DOWNLOAD_OUTCOMES = ['completed', 'skipped', 'failed']

/** The cleanup categories, in the order the page shows them. */
export const CLEANUP_KEYS = ['duplicates', 'working', 'leftovers', 'orphans']

/** Every kind of file a folder scan sorts into, as the page lists them. */
export const FOLDER_KINDS = [
  'audio',
  'podcasts',
  'lyrics',
  'images',
  'playlists',
  'metadata',
  'temporary',
  'other',
]

/** `'M x y L x y ...'` through `coords` (`[{ x, y }]`), or `''`. */
export function linePath(coords) {
  return coords
    .map((c, i) => `${i ? 'L' : 'M'}${round(c.x)} ${round(c.y)}`)
    .join(' ')
}

function round(value) {
  return Math.round(value * 100) / 100
}

/**
 * The growth chart in a `width` x `height` box: where each point sits,
 * the line through the estimated days (`estimated`) and through the
 * measured ones (`measured`), the area under the whole line, and the
 * lowest / highest size shown. The vertical scale starts just under the
 * smallest size, not at zero, so a few gigabytes on a big library still
 * show as growth.
 */
export function growthChart(points, { width = 600, height = 160 } = {}) {
  const list = points || []
  if (!list.length) {
    return { coords: [], estimated: '', measured: '', area: '', min: 0, max: 0 }
  }
  const sizes = list.map((p) => Math.max(0, Number(p.bytes) || 0))
  let min = Math.min(...sizes)
  let max = Math.max(...sizes)
  const span = max - min
  if (span) {
    min = Math.max(0, min - span * 0.08)
    max += span * 0.08
  } else {
    // A flat line sits in the middle rather than on an edge.
    min = Math.max(0, min - (min || 1) * 0.5)
    max += max * 0.5 || 1
  }
  const step = list.length > 1 ? width / (list.length - 1) : 0
  const coords = list.map((point, index) => ({
    x: list.length > 1 ? index * step : width / 2,
    y: height - ((sizes[index] - min) / (max - min)) * height,
    point,
  }))
  // Estimated days come first; the dashed line runs up to the first
  // measured one so the two halves meet.
  const firstMeasured = list.findIndex((p) => !p.estimated)
  const split = firstMeasured < 0 ? list.length - 1 : firstMeasured
  const estimated = split > 0 ? linePath(coords.slice(0, split + 1)) : ''
  const measured = firstMeasured < 0 ? '' : linePath(coords.slice(split))
  const area =
    coords.length > 1
      ? `${linePath(coords)} L${round(width)} ${height} L0 ${height} Z`
      : ''
  return { coords, estimated, measured, area, min, max }
}

/** Which of `count` evenly spread points is nearest to `fraction` of
 * the way across (0-1). */
export function nearestIndex(fraction, count) {
  if (count <= 1) return 0
  return Math.round(Math.min(1, Math.max(0, fraction)) * (count - 1))
}

/** `[{ id, files, bytes, share }]` from a `[{ id, files, bytes }]`
 * breakdown; `share` is of the biggest row, for a bar's width. */
export function breakdownRows(items) {
  const rows = (items || []).filter((row) => row.files || row.bytes)
  const top = Math.max(1, ...rows.map((row) => row.bytes || 0))
  return rows.map((row) => ({
    id: row.id,
    files: row.files || 0,
    bytes: row.bytes || 0,
    share: (row.bytes || 0) / top,
  }))
}

/** The library's providers, each with what came in during the period
 * (`added`, `addedFiles`). */
export function providerRows(library, period) {
  const added = new Map((period?.by_provider || []).map((row) => [row.id, row]))
  return breakdownRows(library?.by_provider).map((row) => ({
    ...row,
    added: added.get(row.id)?.bytes || 0,
    addedFiles: added.get(row.id)?.files || 0,
  }))
}

/** A folder's kinds, biggest first: `[{ id, files, bytes, share }]`. */
export function folderKinds(folder) {
  const kinds = folder?.kinds || {}
  return breakdownRows(
    FOLDER_KINDS.filter((id) => kinds[id]).map((id) => ({
      id,
      files: kinds[id].files,
      bytes: kinds[id].bytes,
    }))
  ).sort((a, b) => b.bytes - a.bytes)
}

/** `{ duplicates, working, leftovers, orphans }` as `{ files, bytes }`,
 * plus their `total` - the scan's two are `null` until it is in. */
export function cleanupSummary(report, scan) {
  const pick = (part) =>
    part ? { files: part.files || 0, bytes: part.bytes || 0 } : null
  const parts = {
    duplicates: pick(report?.duplicates),
    working: pick(report?.working),
    leftovers: pick(scan?.leftovers),
    orphans: pick(scan?.orphans),
  }
  const known = Object.values(parts).filter(Boolean)
  return {
    ...parts,
    total: {
      files: known.reduce((sum, part) => sum + part.files, 0),
      bytes: known.reduce((sum, part) => sum + part.bytes, 0),
    },
  }
}

/** Bar heights between 0 and 1 for each outcome's series:
 * `{ completed: [...], skipped: [...], failed: [...] }`, all on one
 * scale so the rows compare. */
export function outcomeBars(series) {
  const rows = series || []
  const top = Math.max(
    1,
    ...rows.flatMap((bucket) => DOWNLOAD_OUTCOMES.map((o) => bucket[o] || 0))
  )
  return Object.fromEntries(
    DOWNLOAD_OUTCOMES.map((outcome) => [
      outcome,
      rows.map((bucket) => ({
        count: bucket[outcome] || 0,
        height: (bucket[outcome] || 0) / top,
      })),
    ])
  )
}

/** Days to a full disk past this aren't worth showing. */
export const FORECAST_MAX_DAYS = 3650

/** How urgent the days left before the disk fills are: `danger`
 * (under a month), `warn` (under a quarter) or `''`. */
export function daysLeftTone(days) {
  if (days === null || days === undefined) return ''
  if (days < 30) return 'danger'
  if (days < 90) return 'warn'
  return ''
}

/** The first estimated day's successor: when the measured sizes start
 * on the chart (`null` when nothing is estimated or all of it is). */
export function measuredFrom(points) {
  const list = points || []
  const index = list.findIndex((p) => !p.estimated)
  if (index <= 0 || !list.some((p) => p.estimated)) return null
  return list[index].day
}

/** `2026-10-27` as the UI language writes a short date. */
export function formatDay(day, locale = 'en') {
  const date = new Date(`${day}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) return String(day || '')
  try {
    return date.toLocaleDateString(locale, {
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC',
    })
  } catch {
    return date.toISOString().slice(0, 10)
  }
}
