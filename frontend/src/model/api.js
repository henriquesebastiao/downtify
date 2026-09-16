// small file used as placeholder/settings for API calls via axios to server-side
import axios from 'axios' // used to connect to server backend in ./server folder
import config from '/src/config.js'

import { v4 as uuidv4 } from 'uuid'

console.log('using env:', process.env)
console.log('using config: ', config)

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

const sessionID = uuidv4()
console.log('session ID: ', sessionID)

getVersion()

const wsConnection = new WebSocket(
  `${config.WS_PROTOCOL}//${config.BACKEND}${
    config.PORT !== '' ? ':' + config.PORT : ''
  }${config.BASEURL}/api/ws?client_id=${sessionID}`
)

wsConnection.onopen = (event) => {
  console.log('websocket connection opened', event)
}

function getVersion() {
  API.get('/api/version')
    .then((res) => {
      const prevItem = localStorage.getItem('version')
      console.log('Backend version: ', res.data)
      localStorage.setItem('version', res.data)
      if (prevItem != res.data) {
        location.reload()
      }
    })
    .catch((error) => {
      console.error(error)
      console.log('Error getting version, using 0')
      localStorage.setItem('version', '0.0.0')
    })
}

function search(query) {
  return API.get('/api/songs/search', { params: { query } })
}

function searchAlbums(query) {
  return API.get('/api/albums/search', { params: { query } })
}

function open(songURL) {
  return API.get('/api/song/url', { params: { url: songURL } })
}

function download(songURL) {
  const url = typeof songURL === 'string' ? songURL : songURL.url
  const hints = typeof songURL === 'string' ? undefined : songURL
  return API.post('/api/download/url', hints, {
    params: { url, client_id: sessionID },
  })
}

function downloadBatch(payload) {
  return API.post('/api/download/batch', payload)
}

function downloadCsv(payload) {
  return API.post('/api/download/csv', payload)
}

function getIncompletePlaylists() {
  return API.get('/api/playlists/incomplete')
}

function getPlaylistBatches() {
  return API.get('/api/playlists/batches')
}

function getPlaylistBatchDetails(spotifyPlaylistId, { tracks = true } = {}) {
  return API.get(
    `/api/playlists/batches/${encodeURIComponent(spotifyPlaylistId)}`,
    { params: tracks ? {} : { tracks: false } }
  )
}

function downloadMissingPlaylistTracks(payload) {
  return API.post('/api/playlists/incomplete/download-missing', payload)
}

function deletePlaylistBatch(spotifyPlaylistId) {
  return API.delete(
    `/api/playlists/batches/${encodeURIComponent(spotifyPlaylistId)}`
  )
}

function check_for_update() {
  return API.get('/api/check_update')
}

function encodePath(fileName) {
  // Encode each path segment individually so '/' separators survive —
  // playlist downloads land under '<playlist>/<song>.mp3' and we need
  // the URL to hit '/downloads/<playlist>/<song>.mp3' literally.
  return String(fileName || '')
    .split('/')
    .map(encodeURIComponent)
    .join('/')
}

// slskd downloads left in place live outside the downloads folder, so the
// '/downloads' static mount can't serve them; '/media' resolves both.
const SLSKD_LIBRARY_PREFIX = 'slskd/'

function downloadFileURL(fileName) {
  const path = String(fileName || '')
  if (path.startsWith(SLSKD_LIBRARY_PREFIX)) {
    return `/media/${encodePath(path)}`
  }
  return `/downloads/${encodePath(path)}`
}

function decodePathSegment(segment) {
  try {
    return decodeURIComponent(segment)
  } catch {
    return segment
  }
}

/** Filename for the browser save dialog (decoded, no %20 etc.). */
function downloadSaveName(fileNameOrURL) {
  const parts = String(fileNameOrURL || '')
    .split('/')
    .filter(Boolean)
  const last = parts[parts.length - 1]
  return last ? decodePathSegment(last) : 'download'
}

function coverFileURL(fileName) {
  return `/cover?file=${encodeURIComponent(fileName)}`
}

function listDownloads(forceRefresh = false) {
  return API.get('/list', {
    params: forceRefresh ? { refresh: true } : {},
  })
}

function listPlaylists() {
  return API.get('/playlists')
}

function listTracks() {
  return API.get('/tracks')
}

function deleteDownload(file) {
  return API.delete('/delete', { params: { file } })
}

function deleteDownloadsBatch(files) {
  return API.delete('/delete/batch', { data: { files } })
}

function deleteLibraryPlaylist(playlistName) {
  return API.delete('/api/library/playlist', {
    params: { playlist_name: playlistName },
  })
}

function reconcileLibrary() {
  return API.post('/api/library/reconcile')
}

function writePlaylistM3u(payload) {
  return API.post('/api/playlist/m3u', payload)
}

function getQueue() {
  return API.get('/api/queue')
}

function removeQueueItem(songId) {
  return API.delete('/api/queue/item', { params: { song_id: songId } })
}

function clearQueue() {
  return API.delete('/api/queue')
}

function clearCompletedQueue() {
  return API.delete('/api/queue/completed')
}

function getCookiesStatus() {
  return API.get('/api/cookies')
}

// The cookies.txt is sent as the raw request body rather than multipart
// form-data, so the backend doesn't need python-multipart just for this.
function uploadCookies(file) {
  return API.post('/api/cookies', file, {
    headers: { 'Content-Type': 'text/plain' },
  })
}

function deleteCookies() {
  return API.delete('/api/cookies')
}

function getSettings() {
  return API.get('/api/settings', { params: { client_id: sessionID } })
}
function setSettings(settings) {
  return API.post('/api/settings/update', settings, {
    params: { client_id: sessionID },
  })
}

function ws_onmessage(fn) {
  return (wsConnection.onmessage = fn)
}
function ws_onerror(fn) {
  return (wsConnection.onerror = fn)
}

export default {
  search,
  searchAlbums,
  open,
  download,
  downloadBatch,
  downloadCsv,
  getIncompletePlaylists,
  getPlaylistBatches,
  getPlaylistBatchDetails,
  downloadMissingPlaylistTracks,
  deletePlaylistBatch,
  downloadFileURL,
  downloadSaveName,
  coverFileURL,
  listDownloads,
  listPlaylists,
  listTracks,
  deleteDownload,
  deleteDownloadsBatch,
  deleteLibraryPlaylist,
  reconcileLibrary,
  writePlaylistM3u,
  getQueue,
  removeQueueItem,
  clearQueue,
  clearCompletedQueue,
  getSettings,
  setSettings,
  getCookiesStatus,
  uploadCookies,
  deleteCookies,
  check_for_update,
  ws_onmessage,
  ws_onerror,
  getVersion,
}
