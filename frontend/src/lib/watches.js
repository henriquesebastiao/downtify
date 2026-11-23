// Playlist Monitor list helpers: which tab a watch belongs to, what kind
// of watch a pasted link makes, and filtering/sorting.
import { classifyInput } from './input'
import { compareText, fold } from './library'
import { STAT_SORT_KEYS, statValue } from './watchStats'

export const WATCH_KINDS = ['playlist', 'artist']

/**
 * The picture a playlist watch shows on the Monitor page: the cover saved
 * beside its M3U, else the one its service shows (the server decides, see
 * `GET /api/monitor/playlists/{id}/cover`). `''` for an artist watch, which
 * shows the artist's photo instead. The last check is in the address, so a
 * playlist whose picture changed (Spotify's mixes) is fetched again after
 * its next check rather than kept from the browser's cache.
 */
export function watchCoverUrl(item) {
  if (!item?.id || watchKind(item) !== 'playlist') return ''
  const base = `/api/monitor/playlists/${encodeURIComponent(item.id)}/cover`
  return item.last_checked
    ? `${base}?v=${encodeURIComponent(item.last_checked)}`
    : base
}

/** A watch's tab. Rows from before artist watches have no kind. */
export function watchKind(item) {
  return item?.kind === 'artist' ? 'artist' : 'playlist'
}

/**
 * The kind of watch a link would create — 'playlist', 'artist' — or
 * null when it's neither (left to the server to reject).
 */
export function watchKindOfUrl(raw) {
  if (spotifyUserOf(raw)) return null
  const result = classifyInput(raw)
  if (result.kind === 'playlist') return 'playlist'
  if (result.kind === 'artist') return 'artist'
  return null
}

// open.spotify.com/user/<id> (any locale prefix) or spotify:user:<id>.
const SPOTIFY_USER =
  /(?:open\.spotify\.com\/(?:intl-[a-z]{2}(?:-[a-z]{2})?\/)?user\/|^spotify:user:)([^/?#\s:]+)/i

/**
 * The user id of a Spotify *user* link - a listener's account, which
 * can't be watched - or '' for anything else.
 */
export function spotifyUserOf(raw) {
  const match = SPOTIFY_USER.exec(String(raw || '').trim())
  if (!match) return ''
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

/**
 * What a typed artist name to search for would be: the text when it
 * isn't a link (or a Spotify/YouTube id), '' otherwise.
 */
export function artistNameQuery(raw) {
  const text = String(raw || '').trim()
  if (text.length < 2) return ''
  if (/^[a-z][a-z0-9+.-]*:/i.test(text)) return ''
  if (/[\w-]+\.[a-z]{2,}\//i.test(text) || /^www\./i.test(text)) return ''
  return classifyInput(text).type === 'search' ? text : ''
}

/**
 * A name worth searching for from a Spotify user id: a readable handle
 * ('drake'), not a generated one ('31l3kq7x...').
 */
export function nameFromSpotifyUser(id) {
  const text = String(id || '').trim()
  if (!text || text.length > 30 || /\d{4,}/.test(text)) return ''
  // Generated ids are ~25 letters and digits mixed.
  if (text.length >= 20 && /\d/.test(text)) return ''
  return text.replace(/[._]+/g, ' ')
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
  ...STAT_SORT_KEYS,
]

/**
 * `items` ordered by `key`. The statistics keys (see lib/watchStats.js)
 * read `stats`, a `Map(watch id -> stats row)`.
 */
export function sortWatches(items, key, dir = 'desc', stats = null) {
  const sign = dir === 'asc' ? 1 : -1
  return [...items].sort((a, b) => {
    if (STAT_SORT_KEYS.includes(key)) {
      return (
        sign *
        (statValue(stats?.get(a.id), key) - statValue(stats?.get(b.id), key))
      )
    }
    if (key === 'name') return sign * compareText(a.name, b.name)
    if (key === 'created_at' || key === 'last_checked') {
      // Never-checked watches sort as the oldest.
      const at = (value) => (value ? new Date(value).getTime() : 0)
      return sign * (at(a[key]) - at(b[key]))
    }
    return sign * ((a[key] || 0) - (b[key] || 0))
  })
}

// ── Artist watches: which kinds of release they download ──────────────

/** YouTube Music's release kinds, in the order they are shown. */
export const RELEASE_TYPES = ['album', 'single', 'ep']

/** A watch's release types; every kind for rows from before the option. */
export function watchReleaseTypes(item) {
  const types = (item?.release_types || []).filter((type) =>
    RELEASE_TYPES.includes(type)
  )
  return types.length ? types : [...RELEASE_TYPES]
}

/**
 * `types` with `type` switched on or off, kept in RELEASE_TYPES order.
 * The last one left can't be switched off: a watch that downloads no kind
 * of release would silently do nothing.
 */
export function toggleReleaseType(types, type) {
  const on = new Set(types)
  if (on.has(type)) {
    if (on.size === 1) return [...types]
    on.delete(type)
  } else if (RELEASE_TYPES.includes(type)) {
    on.add(type)
  }
  return RELEASE_TYPES.filter((t) => on.has(t))
}

/**
 * What an artist watch's row says about its filters: the release kinds
 * when they aren't all of them (`[]` otherwise), and whether it only
 * downloads new releases.
 */
export function releaseFilterSummary(item) {
  if (watchKind(item) !== 'artist') return { types: [], newOnly: false }
  const types = watchReleaseTypes(item)
  return {
    types: types.length === RELEASE_TYPES.length ? [] : types,
    newOnly: Boolean(item.new_only),
  }
}
