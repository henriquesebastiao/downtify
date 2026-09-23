// Download queue: mirrors the backend's jobs (`GET /api/queue`) and the
// progress events it pushes over the WebSocket.
import { ref } from 'vue'
import { isYouTubePlaylistURL, normalizeSpotifyURL } from '/src/model/url'

import API from '/src/model/api'
import { useSettingsManager } from '/src/model/settings'

const STATUS = {
  QUEUED: 'In Queue',
  DOWNLOADING: 'Downloading...',
  DOWNLOADED: 'Done',
  ERROR: 'Error',
}

const downloadQueue = ref([])
// Bumped on every in-place item change so computed counts refresh.
const queueVersion = ref(0)

function touchQueue() {
  downloadQueue.value = downloadQueue.value.slice()
  queueVersion.value += 1
}

/** Match backend ``_register_job`` / queue keys. */
export function jobSongKey(song) {
  if (!song || typeof song !== 'object') return ''
  return String(song.song_id || song.url || '').trim()
}

class DownloadItem {
  constructor(song) {
    this.song = song
    this.web_status = STATUS.QUEUED
    this.progress = 0
    this.message = ''
    this.provider = ''
    this.web_download_url = null
    this.filename = null
    this.updatedAt = Date.now()
  }
  get key() {
    return jobSongKey(this.song)
  }
  setStatus(status) {
    if (this.web_status === status) return
    this.web_status = status
    this.updatedAt = Date.now()
    touchQueue()
  }
  setDownloading() {
    this.setStatus(STATUS.DOWNLOADING)
  }
  setDownloaded() {
    this.progress = 100
    this.setStatus(STATUS.DOWNLOADED)
  }
  setError() {
    this.setStatus(STATUS.ERROR)
  }
  resetForRetry() {
    this.web_status = STATUS.QUEUED
    this.progress = 0
    this.message = ''
    this.provider = ''
    this.web_download_url = null
    this.filename = null
    this.updatedAt = Date.now()
    touchQueue()
  }
  setFile(filename) {
    if (!filename) return
    this.filename = filename
    this.web_download_url = API.downloadFileURL(filename)
  }
  setWebURL(url) {
    this.web_download_url = url
  }
  setFilename(name) {
    this.filename = name
  }
  isQueued() {
    return this.web_status === STATUS.QUEUED
  }
  isDownloading() {
    return this.web_status === STATUS.DOWNLOADING
  }
  isDownloaded() {
    return this.web_status === STATUS.DOWNLOADED
  }
  isErrored() {
    return this.web_status === STATUS.ERROR
  }
  /** 'active' | 'queued' | 'done' | 'failed' */
  get state() {
    if (this.isErrored()) return 'failed'
    if (this.isDownloaded()) return 'done'
    if (this.isQueued()) return 'queued'
    return 'active'
  }
  wsUpdate(message) {
    let changed = false
    if (message.progress !== undefined && message.progress !== this.progress) {
      this.progress = message.progress
      changed = true
    }
    if (message.message !== undefined && message.message !== this.message) {
      this.message = message.message
      changed = true
    }
    if (message.provider && message.provider !== this.provider) {
      this.provider = message.provider
      changed = true
    }
    if (changed) touchQueue()
  }
}

function applyServerJob(item, job) {
  if (job.provider) item.provider = job.provider
  item.message = job.message || ''
  item.progress = job.progress || 0
  if (job.status === 'done') {
    item.setFile(job.filename)
    item.setDownloaded()
  } else if (job.status === 'error') {
    item.setError()
  } else if (job.status === 'downloading') {
    item.setDownloading()
  } else {
    item.setStatus(STATUS.QUEUED)
  }
  touchQueue()
}

function findItem(song) {
  const key = jobSongKey(song)
  if (!key) return null
  return downloadQueue.value.find((item) => item.key === key) || null
}

function appendSong(song) {
  const item = new DownloadItem(song)
  downloadQueue.value.push(item)
  touchQueue()
  return item
}

function upsertSong(song) {
  const existing = findItem(song)
  if (existing) {
    existing.song = { ...existing.song, ...song }
    existing.resetForRetry()
    return existing
  }
  return appendSong(song)
}

export function useProgressTracker() {
  function removeSong(song) {
    const key = jobSongKey(song)
    downloadQueue.value = downloadQueue.value.filter((item) => item.key !== key)
    touchQueue()
  }
  return {
    appendSong,
    removeSong,
    getBySong: findItem,
    downloadQueue,
    queueVersion,
  }
}

// ── Server sync ──────────────────────────────────────────────────────
let queuePollTimer = null

function queueHasActiveItems() {
  return downloadQueue.value.some(
    (item) => item.isDownloading() || item.isQueued()
  )
}

function stopQueuePoll() {
  if (queuePollTimer) {
    clearInterval(queuePollTimer)
    queuePollTimer = null
  }
}

function ensureQueuePoll() {
  if (!queueHasActiveItems()) {
    stopQueuePoll()
    return
  }
  if (queuePollTimer) return
  queuePollTimer = setInterval(() => {
    syncQueueFromServer().catch(() => {})
  }, 3000)
}

export async function syncQueueFromServer() {
  const res = await API.getQueue()
  for (const job of res.data || []) {
    if (!job.song) continue
    const item = findItem(job.song) || appendSong(job.song)
    applyServerJob(item, job)
  }
  touchQueue()
  if (queueHasActiveItems()) ensureQueuePoll()
  else stopQueuePoll()
}

API.onMessage((data) => {
  if (!data || !data.song) return
  const item = findItem(data.song) || appendSong(data.song)
  if (data.status === 'done') {
    item.wsUpdate(data)
    item.setFile(data.filename)
    item.setDownloaded()
  } else if (data.status === 'error') {
    item.wsUpdate(data)
    item.setError()
  } else if (data.status === 'queued') {
    item.wsUpdate(data)
    item.setStatus(STATUS.QUEUED)
  } else {
    item.wsUpdate(data)
    item.setDownloading()
  }
  // Progress messages can arrive many times a second across parallel
  // downloads; the poll (not every message) reconciles with /api/queue.
  ensureQueuePoll()
})

syncQueueFromServer().catch(() => {})

// ── Actions ──────────────────────────────────────────────────────────
function isPlaylistLink(url) {
  return (
    normalizeSpotifyURL(url).includes('://open.spotify.com/playlist/') ||
    isYouTubePlaylistURL(url)
  )
}

const loading = ref(false)

export function useDownloadManager() {
  const settingsManager = useSettingsManager()

  function generateM3u() {
    return settingsManager.settings.value.generate_m3u !== false
  }

  /**
   * Queue already-resolved songs as one batch. `playlistUrl` makes it a
   * playlist download (folder, M3U, playlist tracking). Without a real
   * playlist behind it (an artist's top songs), `playlistName` and
   * `coverUrl` name the playlist and its cover instead, and `m3u`
   * overrides the "generate M3U" setting for this batch.
   */
  async function fromSongs(
    list,
    { playlistUrl = '', playlistName = '', coverUrl = '', m3u } = {}
  ) {
    const hints = playlistUrl ? { downtify_playlist_url: playlistUrl } : {}
    const songs = list.map((song, i) => ({
      ...song,
      ...hints,
      downtify_track_order: song.downtify_track_order ?? i,
    }))
    for (const song of songs) upsertSong(song)
    touchQueue()
    ensureQueuePoll()
    await API.downloadBatch({
      songs,
      playlist_url: playlistUrl,
      playlist_name: playlistName,
      cover_url: coverUrl,
      generate_m3u: m3u ?? generateM3u(),
    })
    await syncQueueFromServer().catch(() => {})
    return songs.length
  }

  /** Resolve a link and queue everything it points at. */
  async function fromURL(url) {
    loading.value = true
    try {
      const res = await API.open(url)
      const data = res.data
      if (Array.isArray(data)) {
        return await fromSongs(data, {
          playlistUrl: isPlaylistLink(url) ? url : '',
        })
      }
      queue(data)
      return 1
    } finally {
      loading.value = false
    }
  }

  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = () => reject(reader.error || new Error('Read failed'))
      reader.readAsText(file)
    })
  }

  async function fromCsvFile(file, playlistName) {
    loading.value = true
    try {
      const csv = await readFileAsText(file)
      const res = await API.downloadCsv({
        csv,
        playlist_name: playlistName || '',
        generate_m3u: generateM3u(),
      })
      syncQueueFromServer().catch(() => {})
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function download(song) {
    const item = findItem(song) || appendSong(song)
    item.setDownloading()
    try {
      const res = await API.download(song)
      item.setFile(res.data)
      item.setDownloaded()
      return { song, filename: res.data }
    } catch (err) {
      item.message = err?.response?.data?.detail || item.message
      item.setError()
      return { song, filename: null }
    }
  }

  function queue(song, beginDownload = true) {
    upsertSong(song)
    if (beginDownload) return download(song)
    return Promise.resolve({ song, filename: null })
  }

  function retryWithAudio(song, youtubeVideoId) {
    const item = findItem(song)
    if (item) {
      item.song = { ...item.song, youtube_id: youtubeVideoId }
      item.resetForRetry()
    }
    return download({ ...song, youtube_id: youtubeVideoId })
  }

  function remove(song) {
    const songId = jobSongKey(song)
    downloadQueue.value = downloadQueue.value.filter(
      (item) => item.key !== songId
    )
    touchQueue()
    if (songId) API.removeQueueItem(songId).catch(() => {})
  }

  async function clearAll() {
    await API.clearQueue()
    downloadQueue.value = []
    touchQueue()
  }

  async function clearCompleted() {
    await API.clearCompletedQueue()
    downloadQueue.value = downloadQueue.value.filter(
      (item) => !item.isDownloaded()
    )
    touchQueue()
  }

  function retry(song) {
    const item = findItem(song)
    if (item) item.resetForRetry()
    return download(song)
  }

  function retryAllFailed() {
    const failed = downloadQueue.value.filter((item) => item.isErrored())
    for (const item of failed) retry(item.song)
    return failed.length
  }

  return {
    fromURL,
    fromSongs,
    fromCsvFile,
    download,
    queue,
    retry,
    retryWithAudio,
    retryAllFailed,
    remove,
    clearAll,
    clearCompleted,
    loading,
  }
}
