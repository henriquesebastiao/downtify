// Tracks similar to one track, via Last.fm (the Similar page).
import { computed, ref } from 'vue'

import API from '/src/model/api'
import { useLibrary } from '/src/model/library'

const artist = ref('')
const track = ref('')
const tracks = ref([])
const loading = ref(false)
const error = ref('')
const searched = ref(false)
let serial = 0

async function searchFor(seedArtist, seedTrack) {
  const a = String(seedArtist || '').trim()
  const t = String(seedTrack || '').trim()
  artist.value = a
  track.value = t
  if (!a || !t) {
    tracks.value = []
    searched.value = false
    return
  }
  const mine = ++serial
  loading.value = true
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

function clear() {
  serial += 1
  artist.value = ''
  track.value = ''
  tracks.value = []
  loading.value = false
  error.value = ''
  searched.value = false
}

export function useSimilar() {
  const library = useLibrary()
  // The library refreshes itself after downloads; rows follow it so a
  // downloaded similar track shows as in-library without re-searching.
  const songs = computed(() =>
    tracks.value.map((item) => ({
      name: item.title,
      artists: [item.artist],
      artist: item.artist,
      cover_url: item.image_url || '',
      // What preview + download resolution need: artist/title lookup
      // (Deezer clip) and a stable row key. No `url`/`song_id` until a
      // search resolves the row into a downloadable song.
      match: item.match,
      lastfm_url: item.url,
    }))
  )
  return {
    artist,
    track,
    tracks,
    songs,
    loading,
    error,
    searched,
    searchFor,
    clear,
    lookupSongs: library.lookupSongs,
  }
}
