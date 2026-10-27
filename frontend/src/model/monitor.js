import axios from 'axios'
import config from '/src/config.js'

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

function listMonitoredPlaylists() {
  return API.get('/api/monitor/playlists')
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

// Each watch's storage, status and activity over the last `days`.
function getMonitorStats(days = 30) {
  return API.get('/api/monitor/stats', { params: { days } })
}

// Which watch first downloaded a library file, and which hold it now.
function getTrackProvenance(file) {
  return API.get('/api/monitor/provenance', { params: { file } })
}

// A watch's songs, newest first, with how each got there.
function getWatchTracks(id) {
  return API.get(`/api/monitor/playlists/${id}/tracks`)
}

export default {
  getMonitorStats,
  getTrackProvenance,
  getWatchTracks,
  listMonitoredPlaylists,
  addMonitoredPlaylist,
  updateMonitoredPlaylist,
  deleteMonitoredPlaylist,
  checkMonitoredPlaylist,
}
