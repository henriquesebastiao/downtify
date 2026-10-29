// Playlist Monitor statistics and provenance helpers (GET
// /api/monitor/stats, /provenance, /playlists/{id}/tracks): what a
// watch's row shows, how the list sorts by it, and how a watch's songs
// filter. Pure functions - the pages fetch.

/** The periods the activity numbers can cover, in days. */
export const STAT_PERIODS = [7, 30, 90]

/** Sort keys that order watches by their statistics. */
export const STAT_SORT_KEYS = [
  'activity',
  'rate',
  'growth',
  'storage',
  'contributed',
]

/** `Map(watch id -> stats row)` from a stats response. */
export function statsById(data) {
  return new Map((data?.watches || []).map((row) => [row.id, row]))
}

/** The number a statistics sort key orders by (none known: 0). */
export function statValue(stats, key) {
  if (!stats) return 0
  if (key === 'activity') return stats.period?.added || 0
  if (key === 'rate') return stats.rate?.per_day || 0
  if (key === 'growth') return stats.period?.bytes || 0
  if (key === 'storage') return stats.storage?.unique_bytes || 0
  if (key === 'contributed') return stats.status?.downloaded || 0
  return 0
}

const TRENDS = {
  up: { icon: 'trending', flip: false, label: 'watchStats.trendUp' },
  down: { icon: 'trending', flip: true, label: 'watchStats.trendDown' },
  steady: { icon: 'minus', flip: false, label: 'watchStats.trendSteady' },
  idle: { icon: 'minus', flip: false, label: 'watchStats.trendIdle' },
  new: { icon: 'sparkle', flip: false, label: 'watchStats.trendNew' },
}

/** How a trend direction is drawn: an icon (flipped for "down") and
 * the i18n key of its label. */
export function trendDisplay(direction) {
  return TRENDS[direction] || TRENDS.new
}

/** Bar heights between 0 and 1 for a sparkline of `series`. */
export function sparkline(series) {
  const values = (series || []).map((value) => Math.max(0, value || 0))
  const max = Math.max(1, ...values)
  return values.map((value) => value / max)
}

/** A rate (songs per day/week/month) as the UI shows it. */
export function formatRate(value, locale = 'en') {
  const number = Number(value) || 0
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: number && number < 10 ? 1 : 0,
  }).format(number)
}

const PROVIDER_LABELS = {
  'youtube-music': 'settings.sourceYtm',
  youtube: 'settings.sourceYt',
  soundcloud: 'settings.sourceSoundcloud',
  slskd: 'settings.sourceSlskd',
  deemix: 'settings.deemixTitle',
  folder: 'playlistSearch.fromFolders',
  unknown: 'playlistSearch.unknownSource',
  '': 'playlistSearch.unknownSource',
}

/** The i18n key naming an audio provider, or null for one it doesn't
 * know (shown as is). */
export function providerLabelKey(id) {
  return PROVIDER_LABELS[id ?? ''] ?? null
}

/** `[{ id, count, share }]`, most first, from `{ provider: count }`. */
export function providerBreakdown(providers) {
  const entries = Object.entries(providers || {}).filter(([, n]) => n > 0)
  const total = entries.reduce((sum, [, n]) => sum + n, 0)
  return entries
    .sort((a, b) => b[1] - a[1])
    .map(([id, count]) => ({ id, count, share: total ? count / total : 0 }))
}

/** The watch outcome filters a song list offers. */
export const TRACK_FILTERS = [
  'all',
  'recent',
  'downloaded',
  'linked',
  'unknown',
]

function addedTime(track) {
  const at = Date.parse(track?.watch?.added_at || '')
  return Number.isFinite(at) ? at : 0
}

/** Whether a watch's song matches a filter; `recent` is added within
 * the last `days` (the first check's backfill included). */
export function matchesTrackFilter(track, filter, days, now = Date.now()) {
  if (filter === 'recent') return addedTime(track) >= now - days * 86400000
  if (filter === 'downloaded' || filter === 'linked' || filter === 'unknown')
    return (track?.watch?.outcome || 'unknown') === filter
  return true
}

/** `{ filter: count }` for every filter in TRACK_FILTERS. */
export function trackFilterCounts(tracks, days, now = Date.now()) {
  return Object.fromEntries(
    TRACK_FILTERS.map((filter) => [
      filter,
      tracks.filter((track) => matchesTrackFilter(track, filter, days, now))
        .length,
    ])
  )
}

/** Where a watch's songs are listed in the Library: its playlist, or
 * the artist's page for an artist watch. */
export function libraryRouteFor(watch) {
  if (!watch?.name) return null
  return watch.kind === 'artist'
    ? { name: 'Artist', query: { name: watch.name } }
    : { name: 'Playlist', query: { name: watch.name } }
}

/** The watch's own page (its activity and songs). */
export function watchRouteFor(watch) {
  return watch?.id ? { name: 'MonitorWatch', params: { id: watch.id } } : null
}
