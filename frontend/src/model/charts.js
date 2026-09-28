// Deezer's global "what's trending" chart, for the Charts page.
import { ref } from 'vue'

import API from '/src/model/api'

const tracks = ref([])
const albums = ref([])
const artists = ref([])
const playlists = ref([])
const podcasts = ref([])
const loading = ref(false)
const error = ref('')
let loaded = false

async function load({ force = false } = {}) {
  if (loaded && !force) return
  loading.value = true
  error.value = ''
  try {
    const res = await API.getChart()
    tracks.value = res.data?.tracks || []
    albums.value = res.data?.albums || []
    artists.value = res.data?.artists || []
    playlists.value = res.data?.playlists || []
    podcasts.value = res.data?.podcasts || []
    loaded = true
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    loading.value = false
  }
}

export function useCharts() {
  return { tracks, albums, artists, playlists, podcasts, loading, error, load }
}
