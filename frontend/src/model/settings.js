import { ref, computed } from 'vue'

import API from '/src/model/api'

const settings = ref({
  audio_providers: [''],
  youtube: {
    cookies_file: '',
    cookies_from_browser: '',
    download_timeout_seconds: 900,
    cookies_file_exists: false,
    cookies_looks_authenticated: false,
    cookies_auth_names: [],
    cookies_warnings: [],
  },
  slskd: {
    enabled: false,
    base_url: '',
    api_key: '',
    source_dir: '/slskd',
    leave_in_place: true,
    timeout_seconds: 20,
    search_retries: 5,
    search_poll_seconds: 15,
    download_attempts: 5,
    poll_interval_seconds: 5,
    poll_max_attempts: 60,
    download_timeout_seconds: 600,
    queued_timeout_seconds: 180,
    duration_tolerance_seconds: 10,
    duration_tolerance_percent: 15,
    mix_duration_tolerance_percent: 50,
    extensions: ['mp3', 'flac'],
    min_bitrate: 256,
  },
  lyrics_providers: [''],
  download_lyrics: true,
  format: '',
  bitrate: '320',
  output: '',
  generate_m3u: true,
  sync_navidrome: true,
  navidrome: {
    enabled: false,
    url: '',
    username: '',
    password: '',
    admin_username: '',
    admin_password: '',
    public_playlist: false,
    scan_after_download: true,
    scan_wait_seconds: 120,
    scan_poll_seconds: 30,
    client_name: 'Downtify',
    api_version: '1.16.1',
  },
  organize_by_artist: false,
  cache_cover_art: false,
  organize_by_album: false,
  max_parallel_downloads: 3,
  download_delay_seconds: 0,
  cover_resolution: 600,
  download_cover_art: true,
  overwrite_existing_files: true,
  search_albums: true,
  mini_player_enabled: true,
})

const MIN_PARALLEL_DOWNLOADS = 1
const MAX_PARALLEL_DOWNLOADS = 30

const MIN_DOWNLOAD_DELAY_SECONDS = 0
const MAX_DOWNLOAD_DELAY_SECONDS = 300

const MIN_COVER_RESOLUTION = 300
const MAX_COVER_RESOLUTION = 1200

const settingsOptions = {
  audio_providers: ['youtube', 'youtube-music', 'slskd'],
  lyrics_providers: ['lrclib', 'genius', 'musixmatch', 'azlyrics'],
  format: ['mp3', 'flac', 'ogg', 'opus', 'm4a'],
  bitrate: ['128', '192', '256', '320'],
  max_parallel_downloads_presets: [1, 2, 3, 5, 8],
  max_parallel_downloads_min: MIN_PARALLEL_DOWNLOADS,
  max_parallel_downloads_max: MAX_PARALLEL_DOWNLOADS,
  download_delay_seconds_presets: [0, 5, 15, 30, 60],
  download_delay_seconds_min: MIN_DOWNLOAD_DELAY_SECONDS,
  download_delay_seconds_max: MAX_DOWNLOAD_DELAY_SECONDS,
  cover_resolution_presets: [300, 600, 800, 1000, 1200],
  cover_resolution_min: MIN_COVER_RESOLUTION,
  cover_resolution_max: MAX_COVER_RESOLUTION,
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

export function clampCoverResolution(value) {
  const parsed = Number.parseInt(value, 10)
  if (Number.isNaN(parsed)) {
    return MIN_COVER_RESOLUTION
  }
  return Math.min(MAX_COVER_RESOLUTION, Math.max(MIN_COVER_RESOLUTION, parsed))
}

API.getSettings().then((res) => {
  if (res.status === 200) {
    if (import.meta.env.DEV) {
      console.log('Received settings:', res.data)
    }
    settings.value = {
      ...settings.value,
      ...res.data,
      youtube: { ...settings.value.youtube, ...(res.data.youtube || {}) },
      slskd: { ...settings.value.slskd, ...(res.data.slskd || {}) },
      navidrome: { ...settings.value.navidrome, ...(res.data.navidrome || {}) },
    }
  } else {
    console.log('Error loading settings')
  }
})

export function useSettingsManager() {
  const isSaved = ref()
  const saveErrorText = ref('')

  function validateSettings() {
    const slskd = settings.value?.slskd || {}
    if (slskd.enabled) {
      if (!String(slskd.base_url || '').trim()) {
        return 'slskd base URL is required when enabled'
      }
      if (!String(slskd.api_key || '').trim()) {
        return 'slskd API key is required when enabled'
      }
    }
    const nav = settings.value?.navidrome || {}
    if (nav.enabled) {
      if (!String(nav.url || '').trim()) {
        return 'Navidrome URL is required when enabled'
      }
      if (!String(nav.username || '').trim()) {
        return 'Navidrome username is required when enabled'
      }
      if (!String(nav.password || '')) {
        return 'Navidrome password is required when enabled'
      }
    }
    return ''
  }

  function saveSettings() {
    console.log('Saving settings:', settings.value)
    const err = validateSettings()
    if (err) {
      saveErrorText.value = err
      isSaved.value = false
      setTimeout(() => {
        isSaved.value = null
      }, 2500)
      return
    }
    saveErrorText.value = ''
    API.setSettings(settings.value)
      .then((res) => {
        if (res.status === 200) {
          console.log('Saved!')
          isSaved.value = true
          const modal = document.getElementById('settings-modal')
          if (modal && 'checked' in modal) {
            modal.checked = false
          }
          setTimeout(() => {
            isSaved.value = null
          }, 2000)
        } else {
          console.error('Error saving settings.', res)
          saveErrorText.value = 'Could not save settings'
          isSaved.value = false
          setTimeout(() => {
            isSaved.value = null
          }, 2000)
        }
      })
      .catch((error) => {
        const detail = error?.response?.data?.detail
        saveErrorText.value =
          typeof detail === 'string' && detail.trim()
            ? detail
            : 'Could not save settings'
        isSaved.value = false
        setTimeout(() => {
          isSaved.value = null
        }, 2500)
      })
  }
  return { saveSettings, settings, settingsOptions, isSaved, saveErrorText }
}
