// The playlist page's search and filters: over every song of the
// playlist, not only the rows the virtualized track list has rendered (so
// browser find can't see the rest). Pure, so it's unit-testable.
import { filterItems } from './library'

const TRACK_FIELDS = ['title', 'artist', 'album', 'file']
const SONG_FIELDS = ['name', 'artists', 'artist', 'album_name']

// Most useful first; anything else (a future provider) comes after.
const PROVIDER_ORDER = [
  'youtube-music',
  'youtube',
  'soundcloud',
  'slskd',
  'deemix',
  'folder',
]

/** The provider id of a library track: `providers[file]`, '' if unknown. */
export function providerOf(track, providers) {
  return String(providers?.[track.file] || '')
}

/**
 * `[{ id, count }]` of the providers among `tracks`, in a fixed order with
 * unknown ('') last - empty when every track has the same one (a filter
 * that keeps everything is no filter).
 */
export function providerCounts(tracks, providers) {
  const counts = new Map()
  for (const track of tracks) {
    const id = providerOf(track, providers)
    counts.set(id, (counts.get(id) || 0) + 1)
  }
  if (counts.size < 2) return []
  const rank = (id) => {
    if (!id) return PROVIDER_ORDER.length + 1
    const at = PROVIDER_ORDER.indexOf(id)
    return at === -1 ? PROVIDER_ORDER.length : at
  }
  return [...counts.entries()]
    .sort((a, b) => rank(a[0]) - rank(b[0]) || a[0].localeCompare(b[0]))
    .map(([id, count]) => ({ id, count }))
}

/**
 * The playlist's library tracks in view `view` matching `query` (every
 * word, ignoring case and accents, in title / artist / album / file name).
 * Views: `all`, `provider:<id>` (`provider:` = unknown) and `navidrome`
 * (the `unmatched` files).
 */
export function filterPlaylistTracks(
  tracks,
  { query = '', view = 'all', providers = {}, unmatched = [] } = {}
) {
  let list = tracks
  if (view.startsWith('provider:')) {
    const want = view.slice('provider:'.length)
    list = list.filter((track) => providerOf(track, providers) === want)
  } else if (view === 'navidrome') {
    const gone = new Set(unmatched)
    list = list.filter((track) => gone.has(track.file))
  }
  return filterItems(list, query, TRACK_FIELDS)
}

/** Source songs (missing ones) matching `query`: title, artists, album. */
export function filterPlaylistSongs(songs, query) {
  return filterItems(songs, query, SONG_FIELDS)
}

/** Whether a view lists missing source songs rather than library tracks. */
export function isSongView(view) {
  return view === 'missing' || view === 'failed'
}
