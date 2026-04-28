import { ref, computed } from 'vue'

import API from '/src/model/api'

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

// If Websocket connection exists, set status using descriptive events, else, fallback to simple messages.
API.ws_onmessage((event) => {
  // event: MessageEvent
  let data = JSON.parse(event.data)
  progressTracker.getBySong(data.song).wsUpdate(data)
})
API.ws_onerror((event) => {
  // event: MessageEvent
  console.log('websocket error:', event)
})

export function useDownloadManager() {
  const loading = ref(false)
  function fromURL(url, options = {}) {
    const { generateM3u = false } = options
    const isPlaylistURL = (url || '').includes('://open.spotify.com/playlist/')
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
          const downloads = songs.map((song) => {
            console.log('Opened Song:', song)
            return queue(song)
          })
          if (generateM3u && isPlaylistURL) {
            Promise.all(downloads).then((results) => {
              const tracks = results
                .filter((r) => r && r.filename)
                .map((r) => ({
                  filename: r.filename,
                  title: r.song.name,
                  artist: (r.song.artists || []).join(', '),
                  duration: r.song.duration || 0,
                }))
              if (tracks.length === 0) {
                console.log('M3U: no successful tracks, skipping write')
                return
              }
              API.writePlaylistM3u({ playlist_url: url, tracks })
                .then((m3uRes) => {
                  console.log('M3U written:', m3uRes.data)
                })
                .catch((err) => {
                  console.log('M3U write failed:', err.message)
                })
            })
          }
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
