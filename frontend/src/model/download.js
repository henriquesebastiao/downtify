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

class DownloadItem {
  constructor(song) {
    this.song = song
    this.web_status = STATUS.QUEUED
    this.progress = 0
    this.message = ''
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
  setWebURL(URL) {
    this.web_download_url = URL
  }
  setFilename(name) {
    this.filename = name
  }
  isQueued() {
    return this.song.song_id !== undefined ? true : false
    // return this.web_status === STATUS.QUEUED
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
  }
}

export function useProgressTracker() {
  function _findIndex(song) {
    return downloadQueue.value.findIndex(
      (downloadItem) => downloadItem.song.song_id === song.song_id
    )
  }
  function appendSong(song) {
    let downloadItem = new DownloadItem(song)
    downloadQueue.value.push(downloadItem)
  }
  function removeSong(song) {
    console.log('removing', song, song.song_id)
    downloadQueue.value = downloadQueue.value.filter(
      (downloadItem) => downloadItem.song.song_id !== song.song_id
    )
    console.log(downloadQueue.value)
  }

  function getBySong(song) {
    const idx = _findIndex(song)
    if (idx === -1) return null
    return downloadQueue.value[_findIndex(song)]
  }

  return {
    appendSong,
    removeSong,
    getBySong,
    downloadQueue,
  }
}

const progressTracker = useProgressTracker()

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
    item.message = data.message || ''
  } else {
    item.wsUpdate(data)
    if (!item.isDownloading()) item.setDownloading()
  }
})
API.ws_onerror((event) => {
  console.log('websocket error:', event)
})

async function _hydrateFromServer() {
  try {
    const res = await API.getQueue()
    const jobs = res.data || []
    for (const job of jobs) {
      if (downloadQueue.value.some((i) => i.song.song_id === job.song.song_id))
        continue
      const item = new DownloadItem(job.song)
      if (job.status === 'done') {
        item.setDownloaded()
        if (job.filename) {
          item.setWebURL(API.downloadFileURL(job.filename))
          item.setFilename(job.filename)
        }
        item.progress = 100
      } else if (job.status === 'error') {
        item.setError()
        item.message = job.message || ''
      } else if (job.status === 'downloading') {
        item.setDownloading()
        item.progress = job.progress || 0
        item.message = job.message || ''
      } else {
        item.message = job.message || ''
      }
      downloadQueue.value.push(item)
    }
  } catch (e) {
    console.log('Failed to load queue from server:', e)
  }
}

_hydrateFromServer()

export function useDownloadManager() {
  const loading = ref(false)
  const settingsManager = useSettingsManager()
  function fromURL(url) {
    const isPlaylistURL = (url || '').includes('://open.spotify.com/playlist/')
    const generateM3u = settingsManager.settings.value.generate_m3u !== false
    loading.value = true
    return API.open(url)
      .then((res) => {
        console.log('Received Response:', res)
        if (res.status !== 200) {
          console.log('Error:', res)
          return
        }
        const songs = res.data
        if (Array.isArray(songs)) {
          for (const song of songs) {
            if (!progressTracker.getBySong(song)) {
              progressTracker.appendSong(song)
            }
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
    return API.download(song.url)
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
  function remove(song) {
    console.log('removing')
    progressTracker.removeSong(song)
  }

  return {
    fromURL,
    download,
    queue,
    remove,
    loading,
  }
}
