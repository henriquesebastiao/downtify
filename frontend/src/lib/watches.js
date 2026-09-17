// Playlist Monitor list helpers: which tab a watch belongs to, what kind
// of watch a pasted link makes, and filtering/sorting.
import { classifyInput } from './input'
import { compareText, fold } from './library'

export const WATCH_KINDS = ['playlist', 'artist']

/** A watch's tab. Rows from before artist watches have no kind. */
export function watchKind(item) {
  return item?.kind === 'artist' ? 'artist' : 'playlist'
}

/**
 * The kind of watch a link would create — 'playlist', 'artist' — or
 * null when it's neither (left to the server to reject).
 */
export function watchKindOfUrl(raw) {
  const result = classifyInput(raw)
  if (result.kind === 'playlist') return 'playlist'
  if (result.kind === 'artist') return 'artist'
  return null
}

/** `{ playlist: n, artist: n }` */
export function countWatches(items) {
  const counts = { playlist: 0, artist: 0 }
  for (const item of items) counts[watchKind(item)] += 1
  return counts
}

/**
 * Watches of one kind, optionally only paused ones, matching every word
 * of `query` in the name or the link.
 */
export function filterWatches(items, { kind, query = '', paused = false }) {
  const words = fold(query).split(/\s+/).filter(Boolean)
  return items.filter((item) => {
    if (kind && watchKind(item) !== kind) return false
    if (paused && item.enabled) return false
    if (!words.length) return true
    const haystack = fold(`${item.name} ${item.url}`)
    return words.every((word) => haystack.includes(word))
  })
}

export const WATCH_SORT_KEYS = [
  'created_at',
  'name',
  'last_checked',
  'interval_minutes',
  'last_track_count',
]

export function sortWatches(items, key, dir = 'desc') {
  const sign = dir === 'asc' ? 1 : -1
  return [...items].sort((a, b) => {
    if (key === 'name') return sign * compareText(a.name, b.name)
    if (key === 'created_at' || key === 'last_checked') {
      // Never-checked watches sort as the oldest.
      const at = (value) => (value ? new Date(value).getTime() : 0)
      return sign * (at(a[key]) - at(b[key]))
    }
    return sign * ((a[key] || 0) - (b[key] || 0))
  })
}
