import axios from 'axios'
import { ref } from 'vue'
import config from '/src/config'

const http = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
  timeout: 30000,
})
const capabilities = ref(null)
const preferences = ref(null)
const error = ref('')
const account = ref(null)
const djSelection = ref([])
let refreshing = null
let refreshedAt = 0

export const musicAI = {
  capabilities,
  preferences,
  error,
  account,
  djSelection,
  selectForDj(tracks) {
    djSelection.value = tracks.slice(0, 40).map(({ id, title, artist }) => ({ id, title, artist }))
  },
  sourceUrl: `${http.defaults.baseURL}/api/v1/music-ai/source`,
  mediaUrl(path) {
    if (!/^\/api\/v1\/music-ai\/dj\/sessions\/[a-f0-9]{32}\/(media|hls\/index\.m3u8)$/.test(path))
      throw new Error('Adresse de lecture DJ invalide')
    return `${http.defaults.baseURL}${path}`
  },
  async djSessions() {
    return (await http.get('/api/v1/music-ai/dj/sessions')).data.sessions
  },
  async createDj(selection) {
    return (await http.post('/api/v1/music-ai/dj/sessions', selection)).data
  },
  async validateDj(selection) {
    return (await http.post('/api/v1/music-ai/dj/admin/validation-sessions', selection)).data
  },
  async commandDj(id, command) {
    return (await http.post(`/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}/commands`, command)).data
  },
  async continuityDj(id, report) {
    return (await http.post(`/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}/validation`, report)).data
  },
  async stopDj(id) {
    await http.delete(`/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}`)
  },
  async discardDj(id) {
    await http.delete(
      `/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}/cache`
    )
  },
  setAccount(id) {
    if (account.value === id) return
    account.value = id || null
    capabilities.value = null
    preferences.value = null
    djSelection.value = []
    refreshedAt = 0
  },
  async refresh(force = false) {
    if (!account.value) return
    if (refreshing) {
      const previous = refreshing
      await previous.promise
      if (force || previous.owner !== account.value) return this.refresh(force)
      return
    }
    if (!force && Date.now() - refreshedAt < 15000) return
    const flight = { owner: account.value, promise: this.load() }
    refreshing = flight
    try {
      await flight.promise
    } finally {
      if (refreshing === flight) refreshing = null
    }
  },
  async load() {
    const owner = account.value
    error.value = ''
    try {
      const [caps, prefs] = await Promise.all([
        http.get('/api/v1/music-ai/capabilities'),
        http.get('/api/v1/music-ai/preferences'),
      ])
      if (owner !== account.value) return
      capabilities.value = caps.data
      preferences.value = prefs.data.preferences
      refreshedAt = Date.now()
    } catch (failure) {
      if (owner !== account.value) return
      error.value = failure?.response?.data?.detail || failure.message
      capabilities.value = null
      refreshedAt = Date.now()
    }
  },
  async set(key, value) {
    await http.put('/api/v1/music-ai/preferences', { [key]: value })
    await this.refresh(true)
  },
  async setGlobal(key, value) {
    await http.put('/api/v1/music-ai/admin/features', { [key]: value })
    await this.refresh(true)
  },
  async recommendations() {
    return (await http.get('/api/v1/music-ai/recommendations')).data.tracks
  },
  async similar(artist, track, selection = {}) {
    return http.get('/api/v1/music-ai/similar', {
      params: { artist, track, ...selection },
    })
  },
  async externalSimilar(artist, track) {
    return http.get('/api/v1/music-ai/external-similar', {
      params: { artist, track },
    })
  },
  async globalFeatures() {
    return (await http.get('/api/v1/music-ai/admin/features')).data
  },
  async analysisStatus() {
    return (await http.get('/api/v1/music-ai/admin/analyses')).data
  },
  async eraseAnalyses() {
    await http.delete('/api/v1/music-ai/admin/analyses')
    await this.refresh(true)
  },
  async resumeAnalysis() {
    await http.post('/api/v1/music-ai/admin/analysis')
    await this.refresh(true)
  },
  async retryAnalyses() {
    return (await http.post('/api/v1/music-ai/admin/analysis/retry')).data
  },
  async playlist(cadence, mood) {
    return (await http.get(`/api/v1/music-ai/playlists/${cadence}/${mood}`))
      .data.tracks
  },
  async playlists() {
    return (await http.get('/api/v1/music-ai/playlists')).data.playlists
  },
  async forget() {
    await http.delete('/api/v1/music-ai/profile')
    await this.refresh(true)
  },
  async save(name, tracks, source) {
    return (
      await http.post('/api/v1/music-ai/playlists/save', {
        name,
        ids: tracks.map((track) => track.id),
        source,
      })
    ).data
  },
  async playable(tracks) {
    return (
      await http.post('/api/v1/music-ai/playback', {
        ids: tracks.map((track) => track.id),
      })
    ).data.tracks
  },
  async listen(event) {
    return http.post('/api/v1/music-ai/listens', event)
  },
}
