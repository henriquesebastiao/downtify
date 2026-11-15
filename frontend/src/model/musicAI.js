import axios from 'axios'
import { v4 as uuidv4 } from 'uuid'
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
let homeCache, homeFlight
let homeGeneration = 0
const djStatusCache = new Map()
const djConsumer = uuidv4()
const consumerParams = () =>
  capabilities.value?.dj_asset_consumers ? { consumer: djConsumer } : {}

export const musicAI = {
  weeklySetsEnabled() {
    return (
      capabilities.value?.version === 1 &&
      capabilities.value?.dj_weekly_sets === true &&
      ['weekly', 'dj_prepared', 'dj_weekly'].every(
        (key) => capabilities.value?.features?.[key] === true
      )
    )
  },
  async weeklySets() {
    const owner = account.value
    if (!owner || !this.weeklySetsEnabled()) return null
    const value = (await http.get('/api/v1/music-ai/dj/weekly')).data
    return owner === account.value && this.weeklySetsEnabled() ? value : null
  },
  async prepareWeekly(theme, requestId) {
    const owner = account.value
    if (!owner || !this.weeklySetsEnabled())
      throw new Error('Sets hebdomadaires désactivés')
    const value = (
      await http.post(
        `/api/v1/music-ai/dj/weekly/${encodeURIComponent(theme)}`,
        { request_id: requestId }
      )
    ).data
    return owner === account.value && this.weeklySetsEnabled() ? value : null
  },
  async copyDj(id, name, requestId) {
    const owner = account.value
    if (
      !owner ||
      !this.weeklySetsEnabled() ||
      !capabilities.value?.dj_asset_copies
    )
      throw new Error('Copies DJ indisponibles')
    const value = (
      await http.post(
        `/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}/copies`,
        { request_id: requestId, name }
      )
    ).data
    return owner === account.value && this.weeklySetsEnabled() ? value : null
  },
  capabilities,
  preferences,
  error,
  account,
  djSelection,
  selectForDj(tracks) {
    djSelection.value = tracks
      .slice(0, 40)
      .map(({ id, title, artist }) => ({ id, title, artist }))
  },
  sourceUrl: `${http.defaults.baseURL}/api/v1/music-ai/source`,
  coverUrl(id) {
    return `${http.defaults.baseURL}/api/v1/tracks/${encodeURIComponent(id)}/cover?size=160`
  },
  async home() {
    const owner = account.value
    const generation = homeGeneration
    if (!owner) return []
    if (homeCache?.owner === owner && Date.now() - homeCache.at < 60000)
      return homeCache.cards
    if (homeFlight?.owner === owner) return homeFlight.promise
    const flight = { owner, promise: null }
    flight.promise = (async () => {
      const response = await http.get('/api/v1/music-ai/home', {
        headers:
          homeCache?.owner === owner ? { 'If-None-Match': homeCache.etag } : {},
        validateStatus: (status) => status === 200 || status === 304,
      })
      const cards =
        response.status === 304 ? homeCache?.cards || [] : response.data.cards
      if (owner === account.value && generation === homeGeneration)
        homeCache = {
          owner,
          cards,
          at: Date.now(),
          etag: response.headers?.etag,
        }
      return owner === account.value && generation === homeGeneration
        ? cards
        : []
    })()
    homeFlight = flight
    try {
      return await flight.promise
    } finally {
      if (homeFlight === flight) homeFlight = null
    }
  },
  mediaUrl(path) {
    if (
      !/^\/api\/v1\/music-ai\/dj\/sessions\/[a-f0-9]{32}\/(media|hls\/index\.m3u8)$/.test(
        path
      )
    )
      throw new Error('Adresse de lecture DJ invalide')
    const suffix =
      path.endsWith('/media') && capabilities.value?.dj_asset_consumers
        ? `?consumer=${encodeURIComponent(djConsumer)}`
        : ''
    return `${http.defaults.baseURL}${path}${suffix}`
  },
  async djSessions() {
    return (
      await http.get('/api/v1/music-ai/dj/sessions', {
        params: capabilities.value?.dj_light_status ? { summary: true } : {},
      })
    ).data.sessions
  },
  async djSession(id, position) {
    const owner = account.value,
      light = position !== undefined && capabilities.value?.dj_light_status
    const cached = light ? djStatusCache.get(id) : null
    const response = await http.get(
      `/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}`,
      {
        params: {
          ...(light ? { view: 'playback', position } : {}),
          ...consumerParams(),
        },
        headers:
          cached?.owner === owner ? { 'If-None-Match': cached.etag } : {},
        validateStatus: (status) => status === 200 || status === 304,
      }
    )
    const value = response.status === 304 ? cached?.value : response.data
    if (owner !== account.value) return null
    if (light) {
      if (djStatusCache.size > 4) djStatusCache.clear()
      djStatusCache.set(id, {
        owner,
        value,
        etag: response.headers?.etag || cached?.etag,
      })
    }
    return value
  },
  async createDj(selection, options = {}) {
    return (await http.post('/api/v1/music-ai/dj/sessions', selection, options))
      .data
  },
  async cancelDjRequest(nonce) {
    if (capabilities.value?.dj_request_cancel)
      await http.delete(
        `/api/v1/music-ai/dj/requests/${encodeURIComponent(nonce)}`,
        { timeout: 8000 }
      )
  },
  async validateDj(selection) {
    return (
      await http.post(
        '/api/v1/music-ai/dj/admin/validation-sessions',
        selection
      )
    ).data
  },
  async commandDj(id, command) {
    return (
      await http.post(
        `/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}/commands`,
        command,
        { timeout: 8000 }
      )
    ).data
  },
  async continuityDj(id, report) {
    return (
      await http.post(
        `/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}/validation`,
        report
      )
    ).data
  },
  async stopDj(id) {
    await http.delete(
      `/api/v1/music-ai/dj/sessions/${encodeURIComponent(id)}`,
      { timeout: 8000, params: consumerParams() }
    )
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
    homeGeneration++
    djStatusCache.clear()
    homeCache = null
    homeFlight = null
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
      // Retain the last capabilities on a transient failure. Losing a network
      // request is not an instruction to disable a running local player.
      refreshedAt = Date.now()
    }
  },
  async set(key, value) {
    homeGeneration++
    homeFlight = null
    homeCache = null
    await http.put('/api/v1/music-ai/preferences', { [key]: value })
    await this.refresh(true)
  },
  async setGlobal(key, value) {
    homeGeneration++
    homeFlight = null
    homeCache = null
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
  async renewPlaylists(requestId) {
    const owner = account.value
    if (!owner || !capabilities.value?.playlist_refresh)
      throw new Error('Renouvellement indisponible sur ce serveur')
    const response = await http.post('/api/v1/music-ai/playlists/refresh', {
      request_id: requestId,
    })
    if (owner !== account.value) throw new Error('Le compte a changé')
    if (response.data?.accepted !== true)
      throw new Error('Le renouvellement n’a pas été accepté')
    homeGeneration++
    homeCache = null
    homeFlight = null
    return response.data
  },
  async forget() {
    homeGeneration++
    homeCache = null
    homeFlight = null
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
