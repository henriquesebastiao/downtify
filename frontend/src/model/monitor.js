import axios from 'axios'
import config from '/src/config.js'

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

export function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

function upsertMonitoredPlaylist({
  spotify_playlist_id,
  enabled = true,
  interval_minutes = 60,
  check_time = null,
  check_timezone = null,
}) {
  const body = {
    spotify_playlist_id,
    enabled,
    interval_minutes,
  }
  if (check_time) {
    body.check_time = check_time
    body.check_timezone = check_timezone || browserTimezone()
  }
  return API.post('/api/monitor/playlists/upsert', body)
}

function updateMonitoredPlaylist(id, updates) {
  return API.patch(`/api/monitor/playlists/${id}`, updates)
}

function checkMonitoredPlaylist(id) {
  return API.post(`/api/monitor/playlists/${id}/check`)
}

export default {
  browserTimezone,
  upsertMonitoredPlaylist,
  updateMonitoredPlaylist,
  checkMonitoredPlaylist,
}
