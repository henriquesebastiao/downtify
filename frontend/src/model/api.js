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

function open(songURL) {
  return API.get('/api/song/url', { params: { url: songURL } })
}

function download(songURL) {
  return API.post('/api/download/url', null, {
    params: { url: songURL, client_id: sessionID },
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
  return `/downloads/${encodePath(fileName)}`
}

function coverFileURL(fileName) {
  return `/cover?file=${encodeURIComponent(fileName)}`
}

function listDownloads() {
  return API.get('/list')
}

function deleteDownload(file) {
  return API.delete('/delete', { params: { file } })
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
  open,
  download,
  downloadBatch,
  downloadFileURL,
  coverFileURL,
  listDownloads,
  deleteDownload,
  writePlaylistM3u,
  getQueue,
  removeQueueItem,
  clearQueue,
  getSettings,
  setSettings,
  check_for_update,
  ws_onmessage,
  ws_onerror,
  getVersion,
}
