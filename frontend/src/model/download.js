import { ref, computed } from 'vue'

import API from '/src/model/api'
import { useSettingsManager } from '/src/model/settings'

const STATUS = {
  QUEUED: 'In Queue',
  DOWNLOADING: 'Downloading...',
  DOWNLOADED: 'Done',
  ERROR: 'Error',
}

const downloadQueue = ref([])

/** Match backend ``_register_job`` / queue keys. */
function jobSongKey(song) {
  if (!song || typeof song !== 'object') return ''
  return String(song.song_id || song.url || '').trim()
}

function applyServerJob(item, job) {
  if (!item || !job) return
  if (job.provider) item.provider = job.provider
  if (job.status === 'done') {
    item.progress = 100
    item.message = job.message || ''
    if (job.filename) {
      item.setWebURL(API.downloadFileURL(job.filename))
      item.setFilename(job.filename)
    }
    item.setDownloaded()
    return
  }
  if (job.status === 'error') {
    item.setError()
    item.message = job.message || ''
    item.progress = job.progress || 0
    return
  }
  if (job.status === 'downloading') {
    item.setDownloading()
    item.progress = job.progress || 0
    item.message = job.message || ''
    return
  }
  item.web_status = STATUS.QUEUED
  item.progress = job.progress || 0
  item.message = job.message || ''
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
  }
  setDownloading() {
    this.web_status = STATUS.DOWNLOADING
  }
  setDownloaded() {
    this.web_status = STATUS.DOWNLOADED
  }
  setError() {
    this.web_status = STATUS.ERROR
  }
  resetForRetry() {
    this.web_status = STATUS.QUEUED
    this.progress = 0
    this.message = ''
    this.provider = ''
    this.web_download_url = null
    this.filename = null
  }
  setWebURL(URL) {
    this.web_download_url = URL
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
  wsUpdate(message) {
    this.progress = message.progress
    this.message = message.message
    if (message.provider) {
      this.provider = message.provider
    }
  }
}

export function useProgressTracker() {
  function _findIndex(song) {
    const key = jobSongKey(song)
    if (!key) return -1
    return downloadQueue.value.findIndex(
      (downloadItem) => jobSongKey(downloadItem.song) === key
    )
  }
  function appendSong(song) {
    let downloadItem = new DownloadItem(song)
    downloadQueue.value.push(downloadItem)
  }
  function removeSong(song) {
    const key = jobSongKey(song)
    downloadQueue.value = downloadQueue.value.filter(
      (downloadItem) => jobSongKey(downloadItem.song) !== key
    )
  }

  function getBySong(song) {
    const idx = _findIndex(song)
    if (idx === -1) return null
    return downloadQueue.value[idx]
  }

  return {
    appendSong,
    removeSong,
    getBySong,
    downloadQueue,
  }
}

const progressTracker = useProgressTracker()

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
  const jobs = res.data || []
  for (const job of jobs) {
    const song = job.song
    if (!song) continue
    let item = progressTracker.getBySong(song)
    if (!item) {
      item = new DownloadItem(song)
      downloadQueue.value.push(item)
    }
    applyServerJob(item, job)
  }
  if (queueHasActiveItems()) {
    ensureQueuePoll()
  } else {
    stopQueuePoll()
  }
}

API.ws_onmessage((event) => {
  let data = JSON.parse(event.data)
  let item = progressTracker.getBySong(data.song)
  if (!item) {
    progressTracker.appendSong(data.song)
    item = progressTracker.getBySong(data.song)
    if (!item) return
  }
  if (data.status === 'done') {
    item.progress = 100
    if (data.filename) {
      item.setWebURL(API.downloadFileURL(data.filename))
      item.setFilename(data.filename)
    }
    item.setDownloaded()
  } else if (data.status === 'error') {
    item.wsUpdate(data)
    item.setError()
  } else if (data.status === 'queued') {
    item.web_status = STATUS.QUEUED
    item.message = data.message || ''
    if (data.provider) item.provider = data.provider
  } else {
    item.wsUpdate(data)
    item.setDownloading()
  }
  ensureQueuePoll()
  syncQueueFromServer().catch(() => {})
})
API.ws_onerror((event) => {
  console.log('websocket error:', event)
})

async function _hydrateFromServer() {
  try {
    await syncQueueFromServer()
  } catch (e) {
    console.log('Failed to load queue from server:', e)
  }
}

_hydrateFromServer()

export function useDownloadManager() {
  const loading = ref(false)
  const settingsManager = useSettingsManager()
  async function pruneCompletedForNewPlaylist() {
    downloadQueue.value = downloadQueue.value.filter(
      (item) => !item.isDownloaded()
    )
    try {
      await API.clearCompletedQueue()
    } catch (e) {
      console.log('Failed to clear completed queue on server:', e)
    }
  }

  function fromURL(url) {
    const isPlaylistURL = (url || '').includes('://open.spotify.com/playlist/')
    const generateM3u = settingsManager.settings.value.generate_m3u !== false
    loading.value = true
    const playlistPrep = isPlaylistURL
      ? pruneCompletedForNewPlaylist()
      : Promise.resolve()
    return playlistPrep
      .then(() => API.open(url))
      .then((res) => {
        console.log('Received Response:', res)
        if (res.status !== 200) {
          console.log('Error:', res)
          return
        }
        const songs = res.data
        if (Array.isArray(songs)) {
          const batchPlaylist = isPlaylistURL
            ? { downtify_playlist_url: url }
            : {}
          for (let i = 0; i < songs.length; i++) {
            const song = {
              ...songs[i],
              ...batchPlaylist,
              downtify_track_order: i,
            }
            if (!progressTracker.getBySong(song)) {
              progressTracker.appendSong(song)
            }
            songs[i] = song
          }
          return API.downloadBatch({
            songs,
            playlist_url: isPlaylistURL ? url : '',
            generate_m3u: generateM3u,
          }).catch((err) => {
            console.log('Batch submit failed:', err.message)
          })
        } else {
          console.log('Opened Song:', songs)
          queue(songs)
        }
      })
      .catch((err) => {
        console.log('Other Error:', err.message)
      })
      .finally(() => {
        loading.value = false
      })
  }

  function download(song) {
    console.log('Downloading', song)
    progressTracker.getBySong(song).setDownloading()
    return API.download(song)
      .then((res) => {
        console.log('Received Response:', res)
        if (res.status === 200) {
          let filename = res.data
          console.log('Download Complete:', filename)
          progressTracker
            .getBySong(song)
            .setWebURL(API.downloadFileURL(filename))
          progressTracker.getBySong(song).setFilename(filename)
          progressTracker.getBySong(song).setDownloaded()
          return { song, filename }
        } else {
          console.log('Error:', res)
          progressTracker.getBySong(song).setError()
          return { song, filename: null }
        }
      })
      .catch((err) => {
        console.log('Other Error:', err.message)
        progressTracker.getBySong(song).setError()
        return { song, filename: null }
      })
  }

  function queue(song, beginDownload = true) {
    progressTracker.appendSong(song)
    if (beginDownload) return download(song)
    return Promise.resolve({ song, filename: null })
  }

  function retryWithAudio(song, youtubeVideoId) {
    const overriddenSong = { ...song, youtube_id: youtubeVideoId }
    const item = progressTracker.getBySong(song)
    if (item) {
      item.song.youtube_id = youtubeVideoId
      item.setDownloading()
      item.progress = 0
      item.message = ''
    }
    return API.download(overriddenSong)
      .then((res) => {
        const it = progressTracker.getBySong(overriddenSong)
        if (res.status === 200) {
          const filename = res.data
          if (it) {
            it.setWebURL(API.downloadFileURL(filename))
            it.setFilename(filename)
            it.setDownloaded()
          }
          return { song: overriddenSong, filename }
        }
        if (it) it.setError()
        return { song: overriddenSong, filename: null }
      })
      .catch((err) => {
        console.error('retryWithAudio error:', err.message)
        const it = progressTracker.getBySong(overriddenSong)
        if (it) it.setError()
        return { song: overriddenSong, filename: null }
      })
  }

  function remove(song) {
    const songId = String(song.song_id || song.url || '')
    progressTracker.removeSong(song)
    if (songId) {
      API.removeQueueItem(songId).catch(() => {})
    }
  }

  async function clearAll() {
    await API.clearQueue()
    downloadQueue.value = []
  }

  async function clearCompleted() {
    await API.clearCompletedQueue()
    downloadQueue.value = downloadQueue.value.filter(
      (item) => !item.isDownloaded()
    )
  }

  function retry(song) {
    const item = progressTracker.getBySong(song)
    if (item) item.resetForRetry()
    return download(song)
  }

  function retryAllFailed() {
    const failed = downloadQueue.value.filter((item) => item.isErrored())
    for (const item of failed) {
      retry(item.song)
    }
    return failed.length
  }

  return {
    fromURL,
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
