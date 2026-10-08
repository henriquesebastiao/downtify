// Tracks similar to one track, via YouTube Music's own radio mix
// (the Similar page). Needs no API key.
import { computed, ref } from 'vue'

import API from '/src/model/api'
import { useLibrary } from '/src/model/library'

const artist = ref('')
const track = ref('')
const tracks = ref([])
const loading = ref(false)
const error = ref('')
const searched = ref(false)
// The endless list: the radio mix is finite per request, so pages are
// chained by seeding each request from the last row.
const hasMore = ref(true)
const loadingMore = ref(false)
let serial = 0

function songKey(item) {
  const id = String(item?.song_id || '')
    .trim()
    .toLowerCase()
  if (id) return `id:${id}`
  const a = String(
    (Array.isArray(item?.artists) ? item.artists[0] : item?.artist) || ''
  )
    .trim()
    .toLowerCase()
  const n = String(item?.name || '')
    .trim()
    .toLowerCase()
  return `${a}|${n}`
}

async function searchFor(seedArtist, seedTrack) {
  const a = String(seedArtist || '').trim()
  const t = String(seedTrack || '').trim()
  artist.value = a
  track.value = t
  if (!a || !t) {
    tracks.value = []
    searched.value = false
    hasMore.value = true
    return
  }
  const mine = ++serial
  loading.value = true
  loadingMore.value = false
  hasMore.value = true
  error.value = ''
  searched.value = true
  try {
    const res = await API.getSimilarTracks(a, t)
    if (mine !== serial) return
    tracks.value = res.data?.tracks || []
  } catch (err) {
    if (mine !== serial) return
    tracks.value = []
    error.value = err?.response?.data?.detail || err?.message || 'Search failed'
  } finally {
    if (mine === serial) loading.value = false
  }
}

/**
 * Append the next page, seeded from the last row. Returns what was added.
 * A page that adds nothing new (or fails) ends the list.
 */
async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return []
  const list = tracks.value
  if (!list.length) return []
  const seed = list[list.length - 1]
  const seedArtist = String(
    (Array.isArray(seed.artists) ? seed.artists[0] : seed.artist) || ''
  ).trim()
  const seedTrack = String(seed.name || '').trim()
  if (!seedArtist || !seedTrack) {
    hasMore.value = false
    return []
  }
  const mine = serial
  loadingMore.value = true
  try {
    const res = await API.getSimilarTracks(seedArtist, seedTrack)
    if (mine !== serial) return []
    const fresh = (res.data?.tracks || []).filter(
      (item) => !list.some((known) => songKey(known) === songKey(item))
    )
    if (fresh.length) {
      tracks.value = [...list, ...fresh]
      return fresh
    }
    hasMore.value = false
    return []
  } catch {
    // A failed page just ends the endless list; what loaded stays playable.
    if (mine === serial) hasMore.value = false
    return []
  } finally {
    loadingMore.value = false
  }
}

function clear() {
  serial += 1
  artist.value = ''
  track.value = ''
  tracks.value = []
  loading.value = false
  loadingMore.value = false
  hasMore.value = true
  error.value = ''
  searched.value = false
}

export function useSimilar() {
  const library = useLibrary()
  // The library refreshes itself after downloads; rows follow it so a
  // downloaded similar track shows as in-library without re-searching.
  // Rows already carry their video id and link, so they download and
  // stream directly.
  const songs = computed(() =>
    tracks.value.map((item) => ({
      song_id: item.song_id || '',
      name: item.name || '',
      artists: Array.isArray(item.artists)
        ? item.artists
        : [item.artist].filter(Boolean),
      artist: item.artist || '',
      cover_url: item.cover_url || '',
      duration: item.duration || 0,
      url: item.url || '',
      match: item.match || 0,
    }))
  )
  return {
    artist,
    track,
    tracks,
    songs,
    loading,
    loadingMore,
    hasMore,
    error,
    searched,
    searchFor,
    loadMore,
    clear,
    lookupSongs: library.lookupSongs,
  }
}
