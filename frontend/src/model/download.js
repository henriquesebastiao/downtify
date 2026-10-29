// Download queue: mirrors the backend's jobs (`GET /api/queue`) and the
// progress events it pushes over the WebSocket.
import { reactive, ref } from 'vue'
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
// Keep the same reactive objects in the public array and the lookup index.
const itemsByKey = new Map()
let queueBatchDepth = 0
let queueDirty = false

function touchQueue() {
  queueDirty = true
  if (queueBatchDepth) return
  queueDirty = false
  downloadQueue.value = downloadQueue.value.slice()
  queueVersion.value += 1
}

function batchQueueChanges(change) {
  queueBatchDepth += 1
  try {
    return change()
  } finally {
    queueBatchDepth -= 1
    if (!queueBatchDepth && queueDirty) touchQueue()
  }
}

function removeItems(matches) {
  const kept = downloadQueue.value.filter((item) => !matches(item))
  if (kept.length === downloadQueue.value.length) return
  itemsByKey.clear()
  for (const item of kept) {
    if (item.key && !itemsByKey.has(item.key)) itemsByKey.set(item.key, item)
  }
  downloadQueue.value = kept
  touchQueue()
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
    // 1-based place among the waiting jobs (`GET /api/queue`), or null.
    this.position = null
    this.updatedAt = Date.now()
  }
  get key() {
    return jobSongKey(this.song)
  }
  patch(values) {
    let changed = false
    for (const [name, value] of Object.entries(values)) {
      if (this[name] === value) continue
      this[name] = value
      changed = true
    }
    if (changed) touchQueue()
  }
  setStatus(status) {
    if (this.web_status === status) return
    this.patch({ web_status: status, updatedAt: Date.now() })
  }
  setDownloading() {
    this.setStatus(STATUS.DOWNLOADING)
  }
  setDownloaded() {
    batchQueueChanges(() => {
      this.patch({ progress: 100 })
      this.setStatus(STATUS.DOWNLOADED)
    })
  }
  setError() {
    this.setStatus(STATUS.ERROR)
  }
  resetForRetry() {
    this.patch({
      web_status: STATUS.QUEUED,
      progress: 0,
      message: '',
      provider: '',
      web_download_url: null,
      filename: null,
      position: null,
      updatedAt: Date.now(),
    })
  }
  setFile(filename) {
    if (!filename) return
    this.patch({ filename, web_download_url: API.downloadFileURL(filename) })
  }
  setWebURL(url) {
    this.patch({ web_download_url: url })
  }
  setFilename(name) {
    this.patch({ filename: name })
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
    const values = {}
    if (message.progress !== undefined) values.progress = message.progress
    if (message.message !== undefined) values.message = message.message
    if (message.provider) values.provider = message.provider
    if (message.reused) values.provider = ''
    this.patch(values)
  }
}

function applyServerJob(item, job) {
  item.patch({
    ...(job.provider ? { provider: job.provider } : {}),
    message: job.message || '',
    progress: job.status === 'done' ? 100 : job.progress || 0,
    position: job.position ?? null,
  })
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
}

function findItem(song) {
  const key = jobSongKey(song)
  if (!key) return null
  return itemsByKey.get(key) || null
}

function appendSong(song) {
  const item = reactive(new DownloadItem(song))
  downloadQueue.value.push(item)
  // appendSong is also public: preserve first-match behavior for duplicates.
  if (item.key && !itemsByKey.has(item.key)) itemsByKey.set(item.key, item)
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
    removeItems((item) => item.key === key)
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
  batchQueueChanges(() => {
    for (const job of res.data || []) {
      if (!job.song) continue
      const item = findItem(job.song) || appendSong(job.song)
      applyServerJob(item, job)
    }
  })
  if (queueHasActiveItems()) ensureQueuePoll()
  else stopQueuePoll()
}

API.onMessage((data) => {
  if (!data) return
  if (data.type === 'queue_reload') {
    syncQueueFromServer().catch(() => {})
    return
  }
  if (!data.song) return
  batchQueueChanges(() => {
    const item = findItem(data.song) || appendSong(data.song)
    item.wsUpdate(data.status === 'done' ? { ...data, progress: 100 } : data)
    if (data.status === 'done') {
      item.setFile(data.filename)
      item.setDownloaded()
    } else if (data.status === 'error') {
      item.setError()
    } else if (data.status === 'queued') {
      item.setStatus(STATUS.QUEUED)
    } else {
      item.setDownloading()
    }
  })
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
    batchQueueChanges(() => {
      for (const song of songs) upsertSong(song)
    })
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

  // A job that replaced a library file's audio (song.replace) is retried
  // by replacing again - never by downloading the song as a new track.
  async function replaceAgain(song, videoId) {
    const item = findItem(song)
    if (item) item.resetForRetry()
    try {
      await API.replaceAudio(song.replace.file, videoId)
    } catch (err) {
      if (item) {
        item.message = err?.response?.data?.detail || item.message
        item.setError()
      }
    }
  }

  function retryWithAudio(song, youtubeVideoId) {
    if (song.replace) return replaceAgain(song, youtubeVideoId)
    const item = findItem(song)
    if (item) {
      item.song = { ...item.song, youtube_id: youtubeVideoId }
      item.resetForRetry()
    }
    return download({ ...song, youtube_id: youtubeVideoId })
  }

  function remove(song) {
    const songId = jobSongKey(song)
    removeItems((item) => item.key === songId)
    if (songId) API.removeQueueItem(songId).catch(() => {})
  }

  async function clearAll() {
    await API.clearQueue()
    removeItems(() => true)
  }

  async function clearCompleted() {
    await API.clearCompletedQueue()
    removeItems((item) => item.isDownloaded())
  }

  function retry(song) {
    if (song.replace) return replaceAgain(song, song.replace.video_id)
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
