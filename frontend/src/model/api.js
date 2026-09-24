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

// ── Artist photo & banner ───────────────────────────────────────────
function getArtistArt(name) {
  return API.get('/api/artists/art', { params: { name } })
}

// Saved photo/banner URLs for many artists in one call - used by the
// Library page's artist grid so it doesn't send one request per tile.
function getArtistArtBulk(names) {
  return API.post('/api/artists/art/bulk', { names })
}

function searchArtistArt(name) {
  return API.get('/api/artists/art/search', { params: { name } })
}

// `file` (a library track from Spotify) is the reliable way to find the
// artist; `name` is the fallback - an exact-name search - for artists
// none of whose tracks came from Spotify.
function getSpotifyArtistArtCandidate(file, kind, name = '') {
  return API.get('/api/artists/art/spotify_candidate', {
    params: { file, kind, name },
  })
}

function setArtistArtFromUrl(name, kind, imageUrl, source = '') {
  return API.post('/api/artists/art/from_url', {
    name,
    kind,
    image_url: imageUrl,
    source,
  })
}

// The file is sent as the raw request body rather than multipart
// form-data, so the backend doesn't need python-multipart just for this
// (same idea as uploadCookies below).
function uploadArtistArt(name, kind, file, source = '') {
  return API.post('/api/artists/art/upload', file, {
    params: { name, kind, source },
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
  })
}

function deleteArtistArt(name, kind) {
  return API.delete('/api/artists/art', { params: { name, kind } })
}

// ── Artist profile: bio, social links, related artists, platform ids ──
function getArtistProfile(name) {
  return API.get('/api/artists/profile', { params: { name } })
}

// Seeds a brand-new artist's profile the first time it's needed - a
// no-op once a profile already exists, so it's safe to call on every
// visit to an artist's page instead of the plain GET above.
function ensureArtistProfile(name, lang, trackFiles) {
  return API.post('/api/artists/profile/ensure', {
    name,
    lang,
    track_files: trackFiles,
  })
}

// `source` picks whose biography text is saved: 'applemusic' or 'deezer'
// (no fallback to the other one), or 'auto' - Apple Music's, else Deezer's.
function fetchArtistBio(name, lang, source = 'auto') {
  return API.post('/api/artists/profile/bio', { name, lang, source })
}

function saveArtistBio(name, bio) {
  return API.put('/api/artists/profile/bio', { name, bio })
}

function saveArtistSocial(name, social) {
  return API.put('/api/artists/profile/social', { name, social })
}

function open(songURL) {
  return API.get('/api/song/url', { params: { url: songURL } })
}

function resolveUrl(url) {
  return API.get('/api/url/resolve', { params: { url } })
}

function artistTopSongs(url) {
  return API.get('/api/artists/top_songs/url', { params: { url } })
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

// ── Liked songs ──────────────────────────────────────────────────────
function getLikes() {
  return API.get('/api/likes')
}

// Idempotent: sending the state you want twice changes nothing.
function setLike(file, liked) {
  return API.put('/api/likes', { file, liked })
}

function clearLikes() {
  return API.post('/api/likes/clear')
}

// ── Podcasts ───────────────────────────────────────────────────────
function resolvePodcast(url) {
  return API.post('/api/podcasts/resolve', { url })
}

function searchPodcasts(q) {
  return API.get('/api/podcasts/search', { params: { q } })
}

function subscribePodcast(payload) {
  return API.post('/api/podcasts/subscribe', payload)
}

function listPodcastShows() {
  return API.get('/api/podcasts/shows')
}

function getPodcastShow(showId) {
  return API.get(`/api/podcasts/shows/${showId}`)
}

function listPodcastEpisodes(showId, includeDismissed = false) {
  return API.get(`/api/podcasts/shows/${showId}/episodes`, {
    params: { include_dismissed: includeDismissed },
  })
}

function updatePodcastShow(showId, updates) {
  return API.patch(`/api/podcasts/shows/${showId}`, updates)
}

function deletePodcastShow(showId, keepFiles = false) {
  return API.delete(`/api/podcasts/shows/${showId}`, {
    params: { keep_files: keepFiles },
  })
}

function downloadPodcastEpisode(episodeId) {
  return API.post(`/api/podcasts/episodes/${episodeId}/download`)
}

function deletePodcastEpisode(episodeId) {
  return API.delete(`/api/podcasts/episodes/${episodeId}`)
}

// Throttled by the caller; idempotent, so a retried tick is harmless.
function setPodcastPlayback(episodeId, payload) {
  return API.put(`/api/podcasts/episodes/${episodeId}/playback`, payload)
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

// Try an integration with the values as they are in the form, saved or
// not. A failed test is still a 200: the answer says what's wrong.
function testSlskd(config) {
  return API.post('/api/slskd/test', config)
}

function testNavidrome(config) {
  return API.post('/api/navidrome/test', config)
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
  getArtistArt,
  getArtistArtBulk,
  searchArtistArt,
  getSpotifyArtistArtCandidate,
  setArtistArtFromUrl,
  uploadArtistArt,
  deleteArtistArt,
  getArtistProfile,
  ensureArtistProfile,
  fetchArtistBio,
  saveArtistBio,
  saveArtistSocial,
  open,
  resolveUrl,
  artistTopSongs,
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
  getLikes,
  setLike,
  clearLikes,
  resolvePodcast,
  searchPodcasts,
  subscribePodcast,
  listPodcastShows,
  getPodcastShow,
  listPodcastEpisodes,
  updatePodcastShow,
  deletePodcastShow,
  downloadPodcastEpisode,
  deletePodcastEpisode,
  setPodcastPlayback,
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
  testSlskd,
  testNavidrome,
  getCookiesStatus,
  uploadCookies,
  deleteCookies,
  check_for_update,
  onMessage,
  ws_onmessage,
  ws_onerror,
  getVersion,
}
