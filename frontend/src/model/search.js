// Free-text search across YouTube Music songs, albums and artists.
import { ref } from 'vue'

import API from '/src/model/api'
import { useSettingsManager } from '/src/model/settings'

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
  if (!term) {
    songs.value = []
    albums.value = []
    artists.value = []
    return
  }
  const mine = ++serial
  loading.value = true
  error.value = ''
  const { settings } = useSettingsManager()
  const withAlbums = settings.value.search_albums !== false
  // Albums and artists are extras: their failure never hides songs.
  const [songRes, albumRes, artistRes] = await Promise.allSettled([
    API.search(term),
    withAlbums ? API.searchAlbums(term) : Promise.resolve({ data: [] }),
    API.searchArtists(term),
  ])
  if (mine !== serial) return
  if (songRes.status === 'fulfilled') {
    songs.value = songRes.value.data || []
  } else {
    songs.value = []
    error.value =
      songRes.reason?.response?.data?.detail || songRes.reason?.message || ''
  }
  albums.value =
    albumRes.status === 'fulfilled' ? albumRes.value.data || [] : []
  artists.value =
    artistRes.status === 'fulfilled' ? artistRes.value.data || [] : []
  loading.value = false
}

export function useSearch() {
  return { query, songs, albums, artists, loading, error, searchFor }
}
