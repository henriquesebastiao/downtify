// Pure helpers for the Finder page (a Deezer-only search, then an artist ->
// albums -> tracks column view). No Vue, no API - unit-testable.

// How many album ids one track-count request asks for: small enough that
// the first counts show up quickly, the rest filling in batch by batch.
export const TRACK_COUNT_BATCH = 12

/**
 * Where a Finder search row opens in the column view: an artist on its
 * own, an album on its artist with the album selected, a song on its
 * album and artist with the song highlighted. `null` when the row lacks
 * the Deezer id that needs.
 */
export function browseLocation(kind, row) {
  if (!row) return null
  let query = null
  if (kind === 'artist' && row.artist_id) {
    query = { artist: String(row.artist_id) }
  } else if (kind === 'album' && row.artist_id && row.album_id) {
    query = { artist: String(row.artist_id), album: String(row.album_id) }
  } else if (kind === 'song' && row.deezer_artist_id) {
    query = { artist: String(row.deezer_artist_id) }
    if (row.deezer_album_id) {
      query.album = String(row.deezer_album_id)
      if (row.song_id) query.track = String(row.song_id)
    }
  }
  return query ? { name: 'FinderBrowse', query } : null
}

/**
 * The ids of the albums whose track count is still unknown - neither on
 * the row itself nor in `known` - in list order, leaving out any already
 * being asked for (`pending`).
 */
export function missingTrackCounts(albums, known = {}, pending = new Set()) {
  const ids = []
  for (const album of albums || []) {
    const id = String(album?.album_id || '')
    if (!id || pending.has(id) || ids.includes(id)) continue
    if (album.track_count !== null && album.track_count !== undefined) {
      continue
    }
    if (known[id] !== undefined) continue
    ids.push(id)
  }
  return ids
}

/** `[1, 2, 3]`, size 2 -> `[[1, 2], [3]]`. */
export function chunk(list, size) {
  const out = []
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size))
  return out
}

/**
 * The release types a discography has - `{ id, count }`, `id` being the
 * lower-cased `release_type` ('album', 'single', 'ep', 'compilation') -
 * in the order they first appear.
 */
export function releaseTypes(albums) {
  const counts = new Map()
  for (const album of albums || []) {
    const id = String(album?.release_type || 'album').toLowerCase()
    counts.set(id, (counts.get(id) || 0) + 1)
  }
  return [...counts].map(([id, count]) => ({ id, count }))
}

// The narrowest each column (artist, discography, tracks) may be dragged to.
export const COLUMN_MIN = [200, 220, 360]

/**
 * The artist and discography columns' widths (px) as the user dragged them,
 * each kept at its minimum or wider, and together leaving the tracks column
 * - the rest of `total` - at least its own. Widening the artist column past
 * that squeezes the discography column first.
 */
export function clampColumnWidths([artist, albums], total, min = COLUMN_MIN) {
  const first = Math.max(min[0], Math.min(artist, total - min[1] - min[2]))
  const second = Math.max(min[1], Math.min(albums, total - first - min[2]))
  return [Math.round(first), Math.round(second)]
}

/** Whether `album` belongs under the release-type filter `type`. */
export function matchesReleaseType(album, type) {
  if (!type || type === 'all') return true
  return String(album?.release_type || 'album').toLowerCase() === type
}

/** How many recent searches are kept. */
export const RECENT_LIMIT = 10

/**
 * The recent searches once `term` was searched for: it first (only once),
 * at most `limit` of them. A blank term changes nothing.
 */
export function addRecent(list, term, limit = RECENT_LIMIT) {
  const value = String(term || '').trim()
  if (!value) return list || []
  return [value, ...(list || []).filter((item) => item !== value)].slice(
    0,
    limit
  )
}
