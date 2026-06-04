// small file used as placeholder/settings for API calls via axios to server-side
import axios from 'axios' // used to connect to server backend in ./server folder
import config from '/src/config.js'

import { v4 as uuidv4 } from 'uuid'

if (import.meta.env.DEV) {
  console.log('using env:', process.env)
  console.log('using config: ', config)
}

const API = axios.create({
  baseURL: `${config.PROTOCOL}//${config.BACKEND}:${config.PORT}${config.BASEURL}`,
})

const sessionID = uuidv4()
if (import.meta.env.DEV) {
  console.log('session ID: ', sessionID)
}

getVersion()

const wsConnection = new WebSocket(
  `${config.WS_PROTOCOL}//${config.BACKEND}${
    config.PORT !== '' ? ':' + config.PORT : ''
  }${config.BASEURL}/api/ws?client_id=${sessionID}`
)

wsConnection.onopen = (event) => {
  if (import.meta.env.DEV) {
    console.log('websocket connection opened', event)
  }
}

function getVersion() {
  API.get('/api/version')
    .then((res) => {
      const prevItem = localStorage.getItem('version')
      if (import.meta.env.DEV) {
        console.log('Backend version: ', res.data)
      }
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

function downloadFileURL(fileName) {
  return `/media/${encodePath(fileName)}`
}

function decodePathSegment(segment) {
  try {
    return decodeURIComponent(segment)
  } catch {
    return segment
  }
}

/** Stored library path from a /media/... URL or plain relative path. */
function mediaUrlToStoredPath(fileNameOrMediaUrl) {
  let path = String(fileNameOrMediaUrl || '')
  const mediaIdx = path.indexOf('/media/')
  if (mediaIdx >= 0) {
    path = path.slice(mediaIdx + '/media/'.length)
  } else {
    path = path.replace(/^\//, '')
  }
  return path.split('/').filter(Boolean).map(decodePathSegment).join('/')
}

/** Filename for the browser save dialog (decoded, no %20 etc.). */
function downloadSaveName(fileNameOrMediaUrl) {
  const stored = mediaUrlToStoredPath(fileNameOrMediaUrl)
  if (!stored) return 'download'
  const parts = stored.split('/')
  return parts[parts.length - 1] || 'download'
}

function coverFileURL(fileName) {
  return `/cover?file=${encodeURIComponent(fileName)}`
}

function listDownloads(forceRefresh = false) {
  return API.get('/list', {
    params: forceRefresh ? { refresh: true } : {},
  })
}

function deleteDownload(file) {
  return API.delete('/delete', { params: { file } })
}

function deleteDownloadsBatch(files) {
  return API.post('/api/library/delete/batch', { files })
}

function deleteLibraryPlaylist(playlistName) {
  return API.delete('/api/library/playlist', {
    params: { playlist_name: playlistName },
  })
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

function getSettings() {
  return API.get('/api/settings', { params: { client_id: sessionID } })
}
function setSettings(settings) {
  return API.post('/api/settings/update', settings, {
    params: { client_id: sessionID },
  })
}

function uploadYoutubeCookies(file) {
  const form = new FormData()
  form.append('file', file)
  return API.post('/api/settings/youtube-cookies', form, {
    params: { client_id: sessionID },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

function clearYoutubeCookies() {
  return API.delete('/api/settings/youtube-cookies', {
    params: { client_id: sessionID },
  })
}

function reconcileLibrary() {
  return API.post('/api/library/reconcile')
}

function ws_onmessage(fn) {
  return (wsConnection.onmessage = fn)
}
function ws_onerror(fn) {
  return (wsConnection.onerror = fn)
}

export default {
  search,
  open,
  download,
  downloadBatch,
  downloadFileURL,
  downloadSaveName,
  coverFileURL,
  listDownloads,
  deleteDownload,
  deleteDownloadsBatch,
  deleteLibraryPlaylist,
  writePlaylistM3u,
  getQueue,
  removeQueueItem,
  clearQueue,
  clearCompletedQueue,
  getSettings,
  setSettings,
  uploadYoutubeCookies,
  clearYoutubeCookies,
  reconcileLibrary,
  check_for_update,
  ws_onmessage,
  ws_onerror,
  getVersion,
}
