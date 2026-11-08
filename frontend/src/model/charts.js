// Deezer's global "what's trending" chart, for the Charts page.
import { ref, watch } from 'vue'
import { libraryOnly } from '/src/model/musicPolicy'

import API from '/src/model/api'

const tracks = ref([])
const albums = ref([])
const artists = ref([])
const playlists = ref([])
const loading = ref(false)
const error = ref('')
let loaded = false
let serial = 0
watch(libraryOnly, () => {
  serial += 1
  loaded = false
  tracks.value = []
  albums.value = []
  artists.value = []
  playlists.value = []
  loading.value = false
  error.value = ''
})

async function load({ force = false } = {}) {
  if (loaded && !force) return
  const mine = ++serial
  loading.value = true
  error.value = ''
  try {
    const res = await API.getChart()
    if (mine !== serial) return
    tracks.value = res.data?.tracks || []
    albums.value = res.data?.albums || []
    artists.value = res.data?.artists || []
    playlists.value = res.data?.playlists || []
    loaded = true
  } catch (err) {
    if (mine !== serial) return
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    if (mine === serial) loading.value = false
  }
}

export function useCharts() {
  return { tracks, albums, artists, playlists, loading, error, load }
}
