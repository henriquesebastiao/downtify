import axios from 'axios'
import config from '/src/config.js'

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

function listMonitoredPlaylists() {
  return API.get('/api/monitor/playlists')
}

function artistSuggestions(offsets = {}) {
  return API.get('/api/monitor/artist-suggestions', {
    params: { limit: 20, ...offsets },
  })
}

function resolveArtistSuggestion(name) {
  return API.get('/api/monitor/artist-suggestions/resolve', {
    params: { name, provider: 'spotify' },
  })
}

// `options`: an artist watch's `release_types` and `new_only`.
function addMonitoredPlaylist(url, intervalMinutes = 60, options = {}) {
  return API.post('/api/monitor/playlists', {
    url,
    interval_minutes: intervalMinutes,
    ...options,
  })
}

function updateMonitoredPlaylist(id, updates) {
  return API.patch(`/api/monitor/playlists/${id}`, updates)
}

function deleteMonitoredPlaylist(id) {
  return API.delete(`/api/monitor/playlists/${id}`)
}

function checkMonitoredPlaylist(id) {
  return API.post(`/api/monitor/playlists/${id}/check`)
}

export default {
  artistSuggestions,
  resolveArtistSuggestion,
  listMonitoredPlaylists,
  addMonitoredPlaylist,
  updateMonitoredPlaylist,
  deleteMonitoredPlaylist,
  checkMonitoredPlaylist,
}
