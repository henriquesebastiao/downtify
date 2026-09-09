import { ref, computed } from 'vue'

import API from '/src/model/api'

const settings = ref({
  audio_providers: [''],
  lyrics_providers: [''],
  download_lyrics: true,
  format: '',
  bitrate: '320',
  output: '',
  generate_m3u: true,
  organize_by_artist: false,
  organize_by_album: false,
  max_parallel_downloads: 3,
  download_delay_seconds: 0,
  search_albums: true,
})

const MIN_PARALLEL_DOWNLOADS = 1
const MAX_PARALLEL_DOWNLOADS = 30

const MIN_DOWNLOAD_DELAY_SECONDS = 0
const MAX_DOWNLOAD_DELAY_SECONDS = 300

const settingsOptions = {
  audio_providers: ['youtube', 'youtube-music'],
  lyrics_providers: ['lrclib', 'genius', 'musixmatch', 'azlyrics'],
  format: ['mp3', 'flac', 'ogg', 'opus', 'm4a'],
  bitrate: ['128', '192', '256', '320'],
  max_parallel_downloads_presets: [1, 2, 3, 5, 8],
  max_parallel_downloads_min: MIN_PARALLEL_DOWNLOADS,
  max_parallel_downloads_max: MAX_PARALLEL_DOWNLOADS,
  download_delay_seconds_presets: [0, 5, 15, 30, 60],
  download_delay_seconds_min: MIN_DOWNLOAD_DELAY_SECONDS,
  download_delay_seconds_max: MAX_DOWNLOAD_DELAY_SECONDS,
  output: '{artists} - {title}.{output-ext}',
}

export function clampParallelDownloads(value) {
  const parsed = Number.parseInt(value, 10)
  if (Number.isNaN(parsed)) {
    return MIN_PARALLEL_DOWNLOADS
  }
  return Math.min(
    MAX_PARALLEL_DOWNLOADS,
    Math.max(MIN_PARALLEL_DOWNLOADS, parsed)
  )
}

export function clampDownloadDelaySeconds(value) {
  const parsed = Number.parseInt(value, 10)
  if (Number.isNaN(parsed)) {
    return MIN_DOWNLOAD_DELAY_SECONDS
  }
  return Math.min(
    MAX_DOWNLOAD_DELAY_SECONDS,
    Math.max(MIN_DOWNLOAD_DELAY_SECONDS, parsed)
  )
}

API.getSettings().then((res) => {
  if (res.status === 200) {
    console.log('Received settings:', res.data)
    settings.value = res.data
  } else {
    console.log('Error loading settings')
  }
})

export function useSettingsManager() {
  const isSaved = ref()
  function saveSettings() {
    console.log('Saving settings:', settings.value)
    API.setSettings(settings.value).then((res) => {
      if (res.status === 200) {
        console.log('Saved!')
        isSaved.value = true
        setTimeout(() => {
          isSaved.value = null
        }, 2000)
      } else {
        console.error('Error saving settings.', res)
        isSaved.value = false
        setTimeout(() => {
          isSaved.value = null
        }, 2000)
      }
    })
  }
  return { saveSettings, settings, settingsOptions, isSaved }
}
