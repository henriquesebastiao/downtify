// The Finder page: a Deezer-only search, then an artist -> albums -> tracks
// column view, with what each fetch returned kept around so going back to
// an artist or album is instant.
import { reactive, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'

import API from '/src/model/api'
import {
  TRACK_COUNT_BATCH,
  addRecent,
  chunk,
  missingTrackCounts,
} from '/src/lib/finder'

// ── Search ────────────────────────────────────────────────────────────
// What is on screen: a search term, or `artist:<Deezer id>` for an artist's
// songs - the answer stays, so showing the same one again asks nothing.
const query = ref('')
// The artist whose songs are on screen ({ id, name }), or null for a search.
const searchedArtist = ref(null)
const songs = ref([])
const albums = ref([])
const artists = ref([])
const loading = ref(false)
const error = ref('')
let serial = 0

function clearResults() {
  songs.value = []
  albums.value = []
  artists.value = []
}

async function run(key, request) {
  query.value = key
  const mine = ++serial
  error.value = ''
  if (!request) {
    clearResults()
    loading.value = false
    return
  }
  loading.value = true
  try {
    const res = await request()
    if (mine !== serial) return
    songs.value = res.data?.songs || []
    albums.value = res.data?.albums || []
    artists.value = res.data?.artists || []
  } catch (err) {
    if (mine !== serial) return
    clearResults()
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    if (mine === serial) loading.value = false
  }
}

function searchFor(text) {
  const term = String(text || '').trim()
  searchedArtist.value = null
  return run(term, term ? () => API.finderSearch(term) : null)
}

/** The key `query` holds while an artist's songs are on screen. */
export function artistSongsKey(artistId) {
  return `artist:${artistId}`
}

/** An artist's songs (their Deezer id, and their name to search for). */
function searchArtistSongs(artistId, name) {
  const id = String(artistId || '').trim()
  searchedArtist.value = id ? { id, name: String(name || '') } : null
  return run(
    artistSongsKey(id),
    id ? () => API.finderArtistSongs(id, name) : null
  )
}

/** The Discover page's query for what was last on screen (see
 * DiscoverHubView): `{ q }` for a search, `{ artist, name }` for an
 * artist's songs, `{}` for nothing. */
function lastSearchQuery() {
  const artist = searchedArtist.value
  if (artist) return { artist: artist.id, name: artist.name }
  return query.value ? { q: query.value } : {}
}

// ── Column view ───────────────────────────────────────────────────────
// Answers by key ('artist:<id>:<lang>', 'albums:<id>', 'album:<id>'): the
// promise while it's on its way, the value once it's back - `peek` hands
// that out synchronously, so a page showing it again never flashes a
// skeleton first. A failed fetch is forgotten, to be tried again.
const CACHE_LIMIT = 200
const promises = new Map()
const values = new Map()

function cached(key, fetch) {
  if (!promises.has(key)) {
    if (promises.size >= CACHE_LIMIT) {
      const oldest = promises.keys().next().value
      promises.delete(oldest)
      values.delete(oldest)
    }
    const promise = fetch().then((res) => {
      values.set(key, res.data)
      return res.data
    })
    promise.catch(() => promises.delete(key))
    promises.set(key, promise)
  }
  return promises.get(key)
}

const keys = {
  artist: (id, lang) => `artist:${id}:${lang}`,
  albums: (id) => `albums:${id}`,
  album: (id) => `album:${id}`,
}

function artist(id, lang) {
  return cached(keys.artist(id, lang), () => API.finderArtist(id, lang))
}

function artistAlbums(id) {
  return cached(keys.albums(id), () => API.finderArtistAlbums(id))
}

function album(id) {
  return cached(keys.album(id), () => API.finderAlbum(id))
}

/** What `artist`/`artistAlbums`/`album` already returned, or `undefined`. */
function peek(kind, ...args) {
  return values.get(keys[kind](...args))
}

// Album id -> track count, for the albums an artist's discography listed
// without one. Filled in batch by batch (see fillTrackCounts).
const trackCounts = reactive({})
const pendingCounts = new Set()

/**
 * Look up the track counts `list` is missing, a batch at a time, while
 * `stillWanted()` - so leaving an artist stops asking for theirs. A batch
 * that fails is just left blank.
 */
async function fillTrackCounts(list, stillWanted = () => true) {
  const ids = missingTrackCounts(list, trackCounts, pendingCounts)
  for (const id of ids) pendingCounts.add(id)
  try {
    for (const batch of chunk(ids, TRACK_COUNT_BATCH)) {
      if (!stillWanted()) break
      try {
        const res = await API.finderTrackCounts(batch)
        Object.assign(trackCounts, res.data || {})
      } catch {
        // Rate limited or unreachable: those rows keep no count.
      }
    }
  } finally {
    for (const id of ids) pendingCounts.delete(id)
  }
}

// ── Recent searches ───────────────────────────────────────────────────
// Kept in this browser only, newest first (see lib/finder.js addRecent).
let recent = null

export function useRecentSearches() {
  recent ??= useLocalStorage('downtify-finder-recent-searches', [])
  return {
    recent,
    remember: (term) => (recent.value = addRecent(recent.value, term)),
    clear: () => (recent.value = []),
  }
}

export function useFinder() {
  return {
    query,
    songs,
    albums,
    artists,
    loading,
    error,
    searchFor,
    searchArtistSongs,
    lastSearchQuery,
    artist,
    artistAlbums,
    album,
    peek,
    trackCounts,
    fillTrackCounts,
  }
}
