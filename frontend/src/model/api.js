// HTTP + WebSocket client for the Downtify backend.
import axios from 'axios'
import config from '/src/config.js'

import { v4 as uuidv4 } from 'uuid'

import { coverURL, fileURL, saveName } from '/src/lib/paths'

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

const sessionID = uuidv4()

// ── Sign-in: a 401 anywhere means this browser has to sign in; a 403
// that something needs an admin is worth telling the user ─────────────
const unauthorizedListeners = new Set()
const forbiddenListeners = new Set()
API.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error?.config?.url || '')
    const status = error?.response?.status
    if (status === 401 && !url.startsWith('/api/auth/')) {
      for (const fn of unauthorizedListeners) fn()
    }
    if (
      status === 403 &&
      error?.response?.data?.detail === 'This needs an admin' &&
      !error?.config?.quiet
    ) {
      for (const fn of forbiddenListeners) fn()
    }
    return Promise.reject(error)
  }
)

/** Called when a request is refused for lack of sign-in. */
function onUnauthorized(fn) {
  unauthorizedListeners.add(fn)
  return () => unauthorizedListeners.delete(fn)
}

/** Called when a signed-in user's request needs an admin. */
function onForbidden(fn) {
  forbiddenListeners.add(fn)
  return () => forbiddenListeners.delete(fn)
}

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

// Deezer's own global "what's trending" chart - `{ tracks, albums, artists }`.
function getChart(limit = 25) {
  return API.get('/api/discover/chart', { params: { limit } })
}

// ── Finder (Deezer-only search and artist/album/track columns) ──────
// `{ songs, albums, artists }`, every row carrying its Deezer ids.
function finderSearch(query) {
  return API.get('/api/finder/search', { params: { query } })
}

function finderArtist(artistId, lang) {
  return API.get('/api/finder/artist', {
    params: { artist_id: artistId, lang },
  })
}

// An artist's songs, shaped like a Finder search (albums/artists empty).
function finderArtistSongs(artistId, name) {
  return API.get('/api/finder/artist/songs', {
    params: { artist_id: artistId, name },
  })
}

function finderArtistAlbums(artistId) {
  return API.get('/api/finder/artist/albums', {
    params: { artist_id: artistId },
  })
}

// `{ <album id>: <track count> }` - up to 50 ids at once.
function finderTrackCounts(albumIds) {
  return API.get('/api/finder/albums/track_counts', {
    params: { ids: albumIds.join(',') },
  })
}

function finderAlbum(albumId) {
  return API.get('/api/finder/album', { params: { album_id: albumId } })
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

// Just the bio text of one service ('applemusic' or 'deezer'), saving
// nothing - for loading it into an editor. Response: `{ bio }`.
function previewArtistBio(name, lang, source) {
  return API.post('/api/artists/profile/bio/preview', { name, lang, source })
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

// The first five Spotify top songs of a library artist, from the file the
// backend keeps per artist (made or refreshed when missing or a week old).
// Same shape as artistTopSongs, plus `fetched_at` and `stale`.
function artistTopSongsSaved(name) {
  return API.get('/api/artists/top_songs/spotify', { params: { name } })
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

function listTracks(params = {}) {
  return API.get('/tracks', { params })
}

function getLibrarySummary() {
  return API.get('/api/library/summary')
}

function getLibraryAlbums() {
  return API.get('/api/library/albums')
}

function getLibraryArtists() {
  return API.get('/api/library/artists')
}

function lookupLibrarySongs(songs) {
  return API.post('/api/library/lookup', { songs })
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

function createLibraryPlaylist(name) {
  return API.post('/api/library/playlists', { name })
}

function editLibraryPlaylistTracks(name, { add = [], remove = [] } = {}) {
  return API.post('/api/library/playlists/tracks', { name, add, remove })
}

function renameLibraryPlaylist(name, newName) {
  return API.post('/api/library/playlists/rename', {
    name,
    new_name: newName,
  })
}

function reconcileLibrary() {
  return API.post('/api/library/reconcile')
}

function syncExternalLibrary(folders) {
  return API.post('/api/library/external/sync', { folders })
}

function getExternalSync() {
  return API.get('/api/library/external/sync')
}

function unmapExternalFolder(folder) {
  return API.post('/api/library/external/unmap', { folder })
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

// ── Sign-in, paired apps and the server's identity ─────────────────
function getAuthStatus() {
  return API.get('/api/auth/status')
}

function login(username, password) {
  return API.post('/api/auth/login', { username, password })
}

function logout() {
  return API.post('/api/auth/logout')
}

// ── Your account ──────────────────────────────────────────────────────
function getMe() {
  return API.get('/api/me')
}

function renameMe(username) {
  return API.patch('/api/me', { username })
}

function changeMyPassword(currentPassword, newPassword) {
  return API.put('/api/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

function setPreferences(prefs) {
  return API.put('/api/me/preferences', prefs)
}

function signOutEverywhere() {
  return API.post('/api/me/sign-out-everywhere')
}

// ── Users and activity (admins) ───────────────────────────────────────
function listUsers() {
  return API.get('/api/users')
}

function createUser(user) {
  return API.post('/api/users', user)
}

function updateUser(id, changes) {
  return API.patch(`/api/users/${encodeURIComponent(id)}`, changes)
}

function deleteUser(id) {
  return API.delete(`/api/users/${encodeURIComponent(id)}`)
}

function getActivity(params = {}) {
  return API.get('/api/activity', { params })
}

function getNowPlaying() {
  return API.get('/api/activity/now')
}

/** Tell the server what this tab plays (for the admins' Activity page). */
function reportPlayback(report) {
  return API.post('/api/activity/playback', report, { quiet: true })
}

function listDevices() {
  return API.get('/api/auth/devices')
}

function renameDevice(id, name) {
  return API.patch(`/api/auth/devices/${encodeURIComponent(id)}`, { name })
}

function revokeDevice(id) {
  return API.delete(`/api/auth/devices/${encodeURIComponent(id)}`)
}

function revokeAll() {
  return API.post('/api/auth/revoke-all')
}

function startPairing() {
  return API.post('/api/auth/pairing')
}

function getPairing(id) {
  return API.get(`/api/auth/pairing/${encodeURIComponent(id)}`)
}

function cancelPairing(id) {
  return API.delete(`/api/auth/pairing/${encodeURIComponent(id)}`)
}

function getServerInfo() {
  return API.get('/api/server/info')
}

function renameServer(name) {
  return API.patch('/api/server', { name })
}

// ── Replacing a track's audio ─────────────────────────────────────
function getReplaceCandidates(file, query = '') {
  return API.get('/api/library/replace/candidates', {
    params: { file, query },
  })
}

function replaceAudio(file, videoId) {
  return API.post('/api/library/replace', { file, video_id: videoId })
}

function getServerPort() {
  return API.get('/api/server/port')
}

/** Save the port; `restart` restarts the server on it right away. */
function setServerPort(port, restart = false) {
  return API.put('/api/server/port', { port: Number(port), restart })
}

// ── Discover ───────────────────────────────────────────────────────
// `library`: [{ name, tracks, liked }] per library artist.
function getDiscover(library) {
  return API.post('/api/discover', { library })
}

// A 30 s clip from Deezer for a song with no `preview_url` of its own.
function findPreview({ artist, title, duration }) {
  return API.get('/api/preview', { params: { artist, title, duration } })
}

// Albums and playlists in two answers: Deezer's first (quick), then what
// Spotify adds, matched to Deezer - see downtify/discover.py.
function getDiscoverDeezerCollections(payload) {
  return API.post('/api/discover/collections/deezer', payload)
}

function getDiscoverSpotifyCollections(payload) {
  return API.post('/api/discover/collections/spotify', payload)
}

function recordListen(artist) {
  return API.post('/api/discover/listens', { artist })
}

function clearListens() {
  return API.delete('/api/discover/listens')
}

function getBlockedArtists() {
  return API.get('/api/discover/blocked')
}

function blockArtist(name) {
  return API.post('/api/discover/blocked', { name })
}

function unblockArtist(name) {
  return API.delete('/api/discover/blocked', { params: { name } })
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

function suggestDirs(path) {
  return API.get('/api/fs/dirs', {
    params: { path: path || '', client_id: sessionID },
  })
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
  getChart,
  finderSearch,
  finderArtist,
  finderArtistSongs,
  finderArtistAlbums,
  finderTrackCounts,
  finderAlbum,
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
  previewArtistBio,
  saveArtistBio,
  saveArtistSocial,
  open,
  resolveUrl,
  artistTopSongs,
  artistTopSongsSaved,
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
  getLibrarySummary,
  getLibraryAlbums,
  getLibraryArtists,
  lookupLibrarySongs,
  getLyrics,
  deleteDownload,
  deleteDownloadsBatch,
  deleteLibraryPlaylist,
  createLibraryPlaylist,
  editLibraryPlaylistTracks,
  renameLibraryPlaylist,
  prepareLibraryArchive,
  libraryArchiveURL,
  reconcileLibrary,
  syncExternalLibrary,
  getExternalSync,
  unmapExternalFolder,
  getLikes,
  setLike,
  clearLikes,
  clientId: sessionID,
  onUnauthorized,
  onForbidden,
  getAuthStatus,
  login,
  logout,
  getMe,
  renameMe,
  changeMyPassword,
  setPreferences,
  signOutEverywhere,
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  getActivity,
  getNowPlaying,
  reportPlayback,
  listDevices,
  renameDevice,
  revokeDevice,
  revokeAll,
  startPairing,
  getPairing,
  cancelPairing,
  getServerInfo,
  renameServer,
  getServerPort,
  setServerPort,
  getReplaceCandidates,
  replaceAudio,
  getDiscover,
  getDiscoverDeezerCollections,
  getDiscoverSpotifyCollections,
  findPreview,
  recordListen,
  clearListens,
  getBlockedArtists,
  blockArtist,
  unblockArtist,
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
  suggestDirs,
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
