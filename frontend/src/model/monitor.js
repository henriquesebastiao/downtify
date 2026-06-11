import axios from 'axios'
import config from '/src/config.js'

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

function upsertMonitoredPlaylist({
  spotify_playlist_id,
  enabled = true,
  interval_minutes = 60,
}) {
  return API.post('/api/monitor/playlists/upsert', {
    spotify_playlist_id,
    enabled,
    interval_minutes,
  })
}

function updateMonitoredPlaylist(id, updates) {
  return API.patch(`/api/monitor/playlists/${id}`, updates)
}

function checkMonitoredPlaylist(id) {
  return API.post(`/api/monitor/playlists/${id}/check`)
}

export default {
  upsertMonitoredPlaylist,
  updateMonitoredPlaylist,
  checkMonitoredPlaylist,
}
