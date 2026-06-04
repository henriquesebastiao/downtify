import { ref, computed } from 'vue'

import API from '/src/model/api'

const VOLUME_KEY = 'downtify-player-volume'
const PLAYER_PLAYLIST_FILTER_KEY = 'downtify-player-pl-filter'
const PLAYER_FILTER_QUERY_KEY = 'downtify-player-filter-query'

export function loadPlayerViewPrefs() {
  try {
    return {
      playlistFilter: sessionStorage.getItem(PLAYER_PLAYLIST_FILTER_KEY) || '',
      filterQuery: sessionStorage.getItem(PLAYER_FILTER_QUERY_KEY) || '',
    }
  } catch {
    return { playlistFilter: '', filterQuery: '' }
  }
}

export function savePlayerViewPrefs(prefs) {
  try {
    if (prefs.playlistFilter !== undefined) {
      sessionStorage.setItem(
        PLAYER_PLAYLIST_FILTER_KEY,
        String(prefs.playlistFilter || '')
      )
    }
    if (prefs.filterQuery !== undefined) {
      sessionStorage.setItem(
        PLAYER_FILTER_QUERY_KEY,
        String(prefs.filterQuery || '')
      )
    }
  } catch {
    // ignore
  }
}

const playlist = ref([])
const currentIndex = ref(-1)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(parseFloat(localStorage.getItem(VOLUME_KEY) || '0.85'))
const isMuted = ref(false)
const repeatMode = ref('off') // 'off' | 'all' | 'one'
const shuffle = ref(false)

let audio = null
let shuffleOrder = []
let shufflePos = 0

function ensureAudio() {
  if (audio) return audio
  audio = new Audio()
  audio.preload = 'metadata'
  audio.volume = volume.value
  audio.addEventListener('timeupdate', () => {
    currentTime.value = audio.currentTime
  })
  audio.addEventListener('loadedmetadata', () => {
    duration.value = isFinite(audio.duration) ? audio.duration : 0
  })
  audio.addEventListener('durationchange', () => {
    duration.value = isFinite(audio.duration) ? audio.duration : 0
  })
  audio.addEventListener('ended', onEnded)
  audio.addEventListener('play', () => {
    isPlaying.value = true
  })
  audio.addEventListener('pause', () => {
    isPlaying.value = false
  })
  return audio
}

function trackFromFile(file) {
  const noExt = file.replace(/\.[^.]+$/, '')
  let artist = ''
  let title = noExt
  const dash = noExt.indexOf(' - ')
  if (dash > 0) {
    artist = noExt.slice(0, dash).trim()
    title = noExt.slice(dash + 3).trim()
  }
  return {
    file,
    url: API.downloadFileURL(file),
    cover: API.coverFileURL(file),
    title,
    artist,
    album: '',
  }
}

/** Normalize ``/list`` rows (string legacy paths or tag-enriched objects). */
export function normalizeLibraryEntry(raw) {
  if (typeof raw === 'string') {
    return trackFromFile(raw)
  }
  const file = String(raw?.file || '')
  const base = trackFromFile(file)
  const title = String(raw?.title || '').trim()
  const artist = String(raw?.artist || '').trim()
  const album = String(raw?.album || '').trim()
  const playlists = Array.isArray(raw?.playlists)
    ? raw.playlists.map((p) => String(p).trim()).filter(Boolean)
    : []
  return {
    file,
    url: base.url,
    cover: base.cover,
    title: title || base.title,
    artist: artist || base.artist,
    album: album || base.album,
    playlists,
    has_cover: Boolean(raw?.has_cover),
  }
}

function buildShuffleOrder() {
  const indices = playlist.value.map((_, i) => i)
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[indices[i], indices[j]] = [indices[j], indices[i]]
  }
  shuffleOrder = indices
  shufflePos =
    currentIndex.value >= 0
      ? Math.max(0, shuffleOrder.indexOf(currentIndex.value))
      : 0
}

function storedPathFromMediaUrl(src) {
  if (!src) return null
  try {
    const path = new URL(src, window.location.origin).pathname
    const prefix = '/media/'
    if (path.startsWith(prefix)) {
      return decodeURIComponent(path.slice(prefix.length))
    }
  } catch {
    /* ignore */
  }
  return null
}

function setPlaylist(files, options = {}) {
  const prevFile =
    currentIndex.value >= 0 && currentIndex.value < playlist.value.length
      ? playlist.value[currentIndex.value]?.file
      : null
  const audioFile = audio?.src ? storedPathFromMediaUrl(audio.src) : null
  const keepFile = prevFile || audioFile || null
  const tracks = (files || []).map((f) =>
    typeof f === 'string' ? trackFromFile(f) : normalizeLibraryEntry(f)
  )
  playlist.value = tracks
  if (shuffle.value) buildShuffleOrder()

  if (options.preservePlayback) {
    if (keepFile) {
      const idx = tracks.findIndex((t) => t.file === keepFile)
      currentIndex.value = idx
      if (idx < 0 && audio && !audio.paused) {
        audio.pause()
      }
    } else if (currentIndex.value >= tracks.length) {
      currentIndex.value = -1
    }
    return
  }

  if (currentIndex.value >= tracks.length) currentIndex.value = -1
  const shouldAutoplay = options.autoplay === true
  if (typeof options.startIndex === 'number') {
    playAt(options.startIndex, { autoplay: shouldAutoplay })
  } else if (shouldAutoplay && tracks.length > 0 && currentIndex.value < 0) {
    playAt(0, { autoplay: true })
  }
}

function playAt(index, options = {}) {
  if (index < 0 || index >= playlist.value.length) return
  const autoplay = options.autoplay !== false
  const a = ensureAudio()
  currentIndex.value = index
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const pos = shuffleOrder.indexOf(index)
    if (pos >= 0) shufflePos = pos
  }
  a.src = playlist.value[index].url
  a.currentTime = 0
  currentTime.value = 0
  if (autoplay) {
    a.play().catch(() => {})
  } else {
    a.pause()
  }
}

function play() {
  if (playlist.value.length === 0) return
  const a = ensureAudio()
  if (currentIndex.value < 0) {
    playAt(0)
    return
  }
  if (!a.src) {
    a.src = playlist.value[currentIndex.value].url
  }
  a.play().catch(() => {})
}

function pause() {
  if (audio) audio.pause()
}

function toggle() {
  if (isPlaying.value) pause()
  else play()
}

function seek(seconds) {
  const a = ensureAudio()
  const max = duration.value || 0
  const clamped = Math.max(0, Math.min(max, seconds))
  a.currentTime = clamped
  currentTime.value = clamped
}

function seekRatio(ratio) {
  if (!duration.value) return
  seek(duration.value * Math.max(0, Math.min(1, ratio)))
}

function setVolume(v) {
  const clamped = Math.max(0, Math.min(1, v))
  volume.value = clamped
  if (audio) audio.volume = clamped
  try {
    localStorage.setItem(VOLUME_KEY, String(clamped))
  } catch {
    // ignore
  }
  if (clamped > 0 && isMuted.value) {
    isMuted.value = false
    if (audio) audio.muted = false
  }
}

function toggleMute() {
  isMuted.value = !isMuted.value
  if (audio) audio.muted = isMuted.value
}

function nextIndex() {
  if (playlist.value.length === 0) return -1
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const nextPos = (shufflePos + 1) % shuffleOrder.length
    return shuffleOrder[nextPos]
  }
  const i = currentIndex.value + 1
  if (i >= playlist.value.length) {
    return repeatMode.value === 'all' ? 0 : -1
  }
  return i
}

function prevIndex() {
  if (playlist.value.length === 0) return -1
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const prevPos = (shufflePos - 1 + shuffleOrder.length) % shuffleOrder.length
    return shuffleOrder[prevPos]
  }
  const i = currentIndex.value - 1
  if (i < 0) {
    return repeatMode.value === 'all' ? playlist.value.length - 1 : 0
  }
  return i
}

function next() {
  const i = nextIndex()
  if (i < 0) {
    pause()
    return
  }
  playAt(i)
}

function prev() {
  const a = ensureAudio()
  if (a.currentTime > 3) {
    seek(0)
    return
  }
  const i = prevIndex()
  if (i < 0) return
  playAt(i)
}

function onEnded() {
  if (repeatMode.value === 'one') {
    seek(0)
    if (audio) audio.play().catch(() => {})
    return
  }
  next()
}

function setRepeat(mode) {
  if (['off', 'all', 'one'].includes(mode)) repeatMode.value = mode
}

function cycleRepeat() {
  const order = ['off', 'all', 'one']
  const i = order.indexOf(repeatMode.value)
  setRepeat(order[(i + 1) % order.length])
}

function setShuffle(v) {
  shuffle.value = !!v
  if (shuffle.value) buildShuffleOrder()
}

function toggleShuffle() {
  setShuffle(!shuffle.value)
}

/** Re-sync UI transport state after remounting the Player view. */
function syncTransportFromAudio() {
  const a = audio
  if (!a?.src) return
  currentTime.value = a.currentTime
  duration.value = isFinite(a.duration) ? a.duration : 0
  isPlaying.value = !a.paused
}

const currentTrack = computed(() =>
  currentIndex.value >= 0 && currentIndex.value < playlist.value.length
    ? playlist.value[currentIndex.value]
    : null
)

const progressPct = computed(() =>
  duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
)

export function formatTime(seconds) {
  if (!isFinite(seconds) || seconds < 0) return '0:00'
  const total = Math.floor(seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function trackInfoFromFile(fileOrEntry) {
  if (typeof fileOrEntry === 'string') {
    return trackFromFile(fileOrEntry)
  }
  return normalizeLibraryEntry(fileOrEntry)
}

export function usePlayer() {
  return {
    playlist,
    currentIndex,
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    progressPct,
    volume,
    isMuted,
    repeatMode,
    shuffle,
    setPlaylist,
    playAt,
    play,
    pause,
    toggle,
    seek,
    seekRatio,
    setVolume,
    toggleMute,
    next,
    prev,
    setRepeat,
    cycleRepeat,
    setShuffle,
    toggleShuffle,
    syncTransportFromAudio,
  }
}
