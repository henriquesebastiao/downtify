import { ref, computed } from 'vue'

import API from '/src/model/api'

const settings = ref({
  audio_providers: ['youtube-music'],
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
  download_cover_art_playlists: false,
  download_cover_art_artist: false,
  download_cover_art_artist_banner: false,
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

// Last state the server confirmed — the settings page compares against
// it to show a "Save changes" bar only when something actually changed.
const saved = ref('')
const loaded = ref(false)

function snapshot() {
  return JSON.stringify(settings.value)
}

API.getSettings()
  .then((res) => {
    // Merge nested blocks over the defaults so a settings file saved
    // before slskd/Navidrome existed still binds every form field.
    settings.value = {
      ...settings.value,
      ...res.data,
      slskd: { ...settings.value.slskd, ...(res.data.slskd || {}) },
      navidrome: { ...settings.value.navidrome, ...(res.data.navidrome || {}) },
    }
    saved.value = snapshot()
    loaded.value = true
  })
  .catch(() => {
    loaded.value = true
  })

const dirty = computed(() => loaded.value && snapshot() !== saved.value)
const isSaved = ref()
const saving = ref(false)
// Backend rejection reason (e.g. slskd enabled without an API key).
const saveErrorText = ref('')

function reset() {
  if (saved.value) settings.value = JSON.parse(saved.value)
}

/** Save everything; resolves true on success. */
async function saveSettings() {
  saving.value = true
  saveErrorText.value = ''
  try {
    const res = await API.setSettings(settings.value)
    settings.value = {
      ...settings.value,
      ...res.data,
      slskd: { ...settings.value.slskd, ...(res.data.slskd || {}) },
      navidrome: { ...settings.value.navidrome, ...(res.data.navidrome || {}) },
    }
    saved.value = snapshot()
    isSaved.value = true
    return true
  } catch (error) {
    const detail = error?.response?.data?.detail
    saveErrorText.value =
      typeof detail === 'string' && detail.trim() ? detail : ''
    isSaved.value = false
    return false
  } finally {
    saving.value = false
    setTimeout(() => {
      isSaved.value = null
    }, 3000)
  }
}

export function useSettingsManager() {
  return {
    saveSettings,
    reset,
    settings,
    settingsOptions,
    isSaved,
    saving,
    dirty,
    loaded,
    saveErrorText,
  }
}
