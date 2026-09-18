// HTTP + WebSocket client for the Downtify backend.
import axios from 'axios'
import config from '/src/config.js'

import { v4 as uuidv4 } from 'uuid'

import { coverURL, fileURL, saveName } from '/src/lib/paths'

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

const sessionID = uuidv4()

getVersion()

// ── WebSocket: progress events, reconnecting with backoff ────────────
const listeners = new Set()
const errorListeners = new Set()
let socket = null
let retryDelay = 1000

function socketURL() {
  const port = config.PORT !== '' ? `:${config.PORT}` : ''
  return `${config.WS_PROTOCOL}//${config.BACKEND}${port}${config.BASEURL}/api/ws?client_id=${sessionID}`
}

function connect() {
  if (typeof WebSocket === 'undefined') return
  socket = new WebSocket(socketURL())
  socket.onopen = () => {
    retryDelay = 1000
  }
  socket.onmessage = (event) => {
    let data
    try {
      data = JSON.parse(event.data)
    } catch {
      return
    }
    for (const fn of listeners) fn(data, event)
  }
  socket.onerror = (event) => {
    for (const fn of errorListeners) fn(event)
  }
  socket.onclose = () => {
    // A restarted backend (container update) comes back on its own.
    setTimeout(connect, retryDelay)
    retryDelay = Math.min(retryDelay * 2, 30000)
  }
}

connect()

/** Subscribe to progress events; returns an unsubscribe function. */
function onMessage(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

function ws_onmessage(fn) {
  return onMessage((data, event) =>
    fn({ ...event, data: JSON.stringify(data) })
  )
}

function ws_onerror(fn) {
  errorListeners.add(fn)
  return () => errorListeners.delete(fn)
}

function getVersion() {
  return API.get('/api/version')
    .then((res) => {
      const prevItem = localStorage.getItem('version')
      localStorage.setItem('version', res.data)
      if (prevItem && prevItem !== res.data) {
        // A new backend ships a new SPA build.
        location.reload()
      }
      return res.data
    })
    .catch(() => {
      localStorage.setItem('version', '0.0.0')
      return '0.0.0'
    })
}

// ── Search & resolve ─────────────────────────────────────────────────
function search(query) {
  return API.get('/api/songs/search', { params: { query } })
}

function searchAlbums(query) {
  return API.get('/api/albums/search', { params: { query } })
}

function searchArtists(query) {
  return API.get('/api/artists/search', { params: { query } })
}

function open(songURL) {
  return API.get('/api/song/url', { params: { url: songURL } })
}

function resolveUrl(url) {
  return API.get('/api/url/resolve', { params: { url } })
}

// ── Downloads ────────────────────────────────────────────────────────
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

function downloadAlbum(url) {
  return API.post('/api/download/album', null, { params: { url } })
}

function downloadCsv(payload) {
  return API.post('/api/download/csv', payload)
}

// ── Playlist download tracking ───────────────────────────────────────
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

// ── Library ──────────────────────────────────────────────────────────
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

function getLyrics(file) {
  return API.get('/lyrics', { params: { file } })
}

function deleteDownload(file) {
  return API.delete('/delete', { params: { file } })
}

function deleteDownloadsBatch(files) {
  return API.delete('/delete/batch', { data: { files } })
}

// Two steps: the selection is POSTed (too long for a URL), then the
// browser navigates to the ticket so the ZIP lands in its downloads
// folder instead of being buffered in memory by fetch.
function prepareLibraryArchive(files) {
  return API.post('/api/library/archive', { files })
}

function libraryArchiveURL(token) {
  return `/api/library/archive/${encodeURIComponent(token)}`
}

function deleteLibraryPlaylist(playlistName) {
  return API.delete('/api/library/playlist', {
    params: { playlist_name: playlistName },
  })
}

function reconcileLibrary() {
  return API.post('/api/library/reconcile')
}

// ── Library upgrade ──────────────────────────────────────────────────
function getLibraryUpgrade() {
  return API.get('/api/library/upgrade')
}

function getLibraryUpgradeJobs(params = {}) {
  return API.get('/api/library/upgrade/jobs', { params })
}

function scanLibraryUpgrade(options = {}) {
  return API.post('/api/library/upgrade/scan', options)
}

function startLibraryUpgrade(categories) {
  return API.post('/api/library/upgrade/start', { categories })
}

function pauseLibraryUpgrade() {
  return API.post('/api/library/upgrade/pause')
}

function resumeLibraryUpgrade() {
  return API.post('/api/library/upgrade/resume')
}

function cancelLibraryUpgrade() {
  return API.post('/api/library/upgrade/cancel')
}

function writePlaylistM3u(payload) {
  return API.post('/api/playlist/m3u', payload)
}

// ── Queue ────────────────────────────────────────────────────────────
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

// ── Settings ─────────────────────────────────────────────────────────
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

export default {
  search,
  searchAlbums,
  searchArtists,
  open,
  resolveUrl,
  download,
  downloadBatch,
  downloadAlbum,
  downloadCsv,
  getIncompletePlaylists,
  getPlaylistBatches,
  getPlaylistBatchDetails,
  downloadMissingPlaylistTracks,
  deletePlaylistBatch,
  downloadFileURL: fileURL,
  downloadSaveName: saveName,
  coverFileURL: coverURL,
  listDownloads,
  listPlaylists,
  listTracks,
  getLyrics,
  deleteDownload,
  deleteDownloadsBatch,
  deleteLibraryPlaylist,
  prepareLibraryArchive,
  libraryArchiveURL,
  reconcileLibrary,
  getLibraryUpgrade,
  getLibraryUpgradeJobs,
  scanLibraryUpgrade,
  startLibraryUpgrade,
  pauseLibraryUpgrade,
  resumeLibraryUpgrade,
  cancelLibraryUpgrade,
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
  onMessage,
  ws_onmessage,
  ws_onerror,
  getVersion,
}
