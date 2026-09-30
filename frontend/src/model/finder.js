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
const query = ref('')
const songs = ref([])
const albums = ref([])
const artists = ref([])
const loading = ref(false)
const error = ref('')
let serial = 0

async function searchFor(text) {
  const term = String(text || '').trim()
  query.value = term
  const mine = ++serial
  error.value = ''
  if (!term) {
    songs.value = []
    albums.value = []
    artists.value = []
    loading.value = false
    return
  }
  loading.value = true
  try {
    const res = await API.finderSearch(term)
    if (mine !== serial) return
    songs.value = res.data?.songs || []
    albums.value = res.data?.albums || []
    artists.value = res.data?.artists || []
  } catch (err) {
    if (mine !== serial) return
    songs.value = []
    albums.value = []
    artists.value = []
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    if (mine === serial) loading.value = false
  }
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
    artist,
    artistAlbums,
    album,
    peek,
    trackCounts,
    fillTrackCounts,
  }
}
