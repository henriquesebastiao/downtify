// Tracks similar to one track - via Last.fm or YouTube Music's own
// radio mix (the Similar page).
import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'

import API from '/src/model/api'
import { useLibrary } from '/src/model/library'

const artist = ref('')
const track = ref('')
const tracks = ref([])
// Where the current answer came from ('lastfm' needs the user's key,
// 'youtube' needs nothing) - remembered between visits.
const source = useLocalStorage('downtify-similar-source', 'lastfm')
const loading = ref(false)
const error = ref('')
const searched = ref(false)
let serial = 0

function validSource(value) {
  return value === 'youtube' ? 'youtube' : 'lastfm'
}

async function searchFor(seedArtist, seedTrack, seedSource) {
  const a = String(seedArtist || '').trim()
  const t = String(seedTrack || '').trim()
  artist.value = a
  track.value = t
  if (seedSource !== undefined) source.value = validSource(seedSource)
  if (!a || !t) {
    tracks.value = []
    searched.value = false
    return
  }
  const mine = ++serial
  const via = source.value
  loading.value = true
  error.value = ''
  searched.value = true
  try {
    const res = await API.getSimilarTracks(a, t, 20, via)
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
  // YouTube rows already carry their video id and link, so they
  // download directly; Last.fm rows only have artist/title until a
  // search resolves them (see SimilarTrackRow).
  const songs = computed(() =>
    tracks.value.map((item) => {
      const artists = Array.isArray(item.artists)
        ? item.artists
        : [item.artist].filter(Boolean)
      const row = {
        name: item.title ?? item.name ?? '',
        artists,
        artist: artists[0] || item.artist || '',
        cover_url: item.cover_url || item.image_url || '',
        duration: item.duration || 0,
        match: item.match || 0,
      }
      if (item.song_id) {
        row.song_id = item.song_id
        row.url = item.url || ''
      } else {
        row.lastfm_url = item.url || ''
      }
      return row
    })
  )
  return {
    artist,
    track,
    tracks,
    songs,
    source,
    loading,
    error,
    searched,
    searchFor,
    clear,
    lookupSongs: library.lookupSongs,
  }
}
