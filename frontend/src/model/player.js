// The built-in player: one <audio> element shared by the mini player and
// the Now playing view, with its queue, shuffle/repeat, sleep timer and
// OS media controls (Media Session).
import { ref, computed, watch } from 'vue'

import { normalizeTrack } from '/src/lib/library'
import { attachEqualizer, resumeEqualizer } from '/src/model/equalizer'
import {
  chunkingSupported,
  createChunkSession,
  ensureVideoId,
  prepareTrack,
} from '/src/model/chunked'
import { resolveTrackUrl } from '/src/model/streamResolve'

const VOLUME_KEY = 'downtify-player-volume'
const RATE_KEY = 'downtify-player-rate'
const SESSION_KEY = 'downtify-player-session'
// Queues past this size aren't persisted across reloads (localStorage
// quota); the player still works, it just starts empty next time.
const MAX_PERSISTED_TRACKS = 2000

// Matches the `sm` breakpoint the mobile-only volume-UI hiding uses.
// Phones control the actual output level with their hardware volume
// buttons, which scale whatever this element outputs — so the element
// itself is kept at full volume there instead of applying the
// desktop-saved level on top of the hardware one.
const MOBILE_VOLUME_BREAKPOINT_PX = 640

function isMobileViewport() {
  return (
    typeof window !== 'undefined' &&
    window.innerWidth < MOBILE_VOLUME_BREAKPOINT_PX
  )
}

function storage() {
  try {
    return typeof localStorage !== 'undefined' ? localStorage : null
  } catch {
    return null
  }
}

const playlist = ref([])
const currentIndex = ref(-1)
const isPlaying = ref(false)
const isBuffering = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(
  isMobileViewport() ? 1 : parseFloat(storage()?.getItem(VOLUME_KEY) || '0.85')
)
const isMuted = ref(false)
// Podcast episodes only, for now — music always plays at 1x. Per device,
// like volume, so a listener doesn't have to reset it every episode.
const playbackRate = ref(parseFloat(storage()?.getItem(RATE_KEY) || '1'))
const repeatMode = ref('off') // 'off' | 'all' | 'one'
const shuffle = ref(false)
// Where the queue came from: { type: 'album'|'playlist'|'artist'|
// 'library'|'search', title, route } — shown as "Playing from".
const context = ref(null)
// Sleep timer: epoch ms to stop at, or 'track' to stop after this one.
const sleepAt = ref(null)
const playError = ref('')
// The unstored stream track being resolved right now (a tap, or the
// queue advancing into it) - rows spin on it. Prefetches don't land
// here: they resolve silently one track ahead.
const resolving = ref(null)

// shuffleOrder is a plain array; this makes `upcoming` notice changes.
const shuffleVersion = ref(0)

let audio = null
let shuffleOrder = []
let shufflePos = 0
let sleepTimer = null
let restoreTime = 0

function ensureAudio() {
  if (audio) return audio
  audio = new Audio()
  // Buffer aggressively: a stream starts while it is still arriving, and
  // the next one is already resolved one track ahead (see prefetchNext).
  audio.preload = 'auto'
  audio.volume = volume.value
  audio.playbackRate = playbackRate.value
  audio.addEventListener('timeupdate', () => {
    currentTime.value = audio.currentTime
    if (chunkSession) {
      try {
        chunkSession.ensureTime(audio.currentTime)
      } catch {
        // Fetch-ahead is best effort; advancing retries.
      }
      watchChunkEnd(audio)
    }
  })
  audio.addEventListener('loadedmetadata', () => {
    duration.value = isFinite(audio.duration) ? audio.duration : 0
    if (restoreTime) {
      audio.currentTime = Math.min(restoreTime, duration.value || 0)
      restoreTime = 0
    }
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
  audio.addEventListener('waiting', () => {
    isBuffering.value = true
  })
  audio.addEventListener('playing', () => {
    isBuffering.value = false
    playError.value = ''
  })
  audio.addEventListener('error', () => {
    isBuffering.value = false
    playError.value = 'unplayable'
  })
  attachEqualizer(audio)
  return audio
}

function toTrack(item) {
  return typeof item === 'string' ? normalizeTrack(item) : item
}

// ── Shuffle order ────────────────────────────────────────────────────
function buildShuffleOrder() {
  const indices = playlist.value.map((_, i) => i)
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[indices[i], indices[j]] = [indices[j], indices[i]]
  }
  // The playing track stays first so shuffling never skips it.
  const current = currentIndex.value
  if (current >= 0) {
    indices.splice(indices.indexOf(current), 1)
    indices.unshift(current)
  }
  shuffleOrder = indices
  shufflePos = 0
  shuffleVersion.value += 1
}

function trackIdentity(track) {
  // Library rows by file; unstored rows by artist/title (stable across
  // resolves - a fresh expiring URL must never count as a new track, or
  // re-selecting the playing queue would restart it).
  if (track?.file) return `file:${track.file}`
  if (track?.stream) return `stream:${track.artist || ''}|${track.title || ''}`
  return `url:${track?.url || ''}`
}

function sameTrackOrder(a, b) {
  if (a.length !== b.length) return false
  return a.every((track, i) => trackIdentity(track) === trackIdentity(b[i]))
}

// ── Queue ────────────────────────────────────────────────────────────
function setPlaylist(files, options = {}) {
  const tracks = (files || []).map(toTrack)
  if (options.context !== undefined) context.value = options.context
  if (
    typeof options.startIndex !== 'number' &&
    sameTrackOrder(tracks, playlist.value)
  ) {
    // Re-selecting the queue that's already loaded must not interrupt
    // what's currently playing.
    return
  }
  playGeneration += 1
  detachChunks()
  playlist.value = tracks
  if (typeof options.startIndex === 'number') {
    if (shuffle.value) {
      currentIndex.value = options.startIndex
      buildShuffleOrder()
    }
    playAt(options.startIndex)
    return
  }
  // Any other queue replacement drops whatever was playing/queued
  // before — a stale currentIndex would otherwise point at an unrelated
  // track in the new list that just happens to share the same position.
  currentIndex.value = -1
  pause()
  if (audio) {
    audio.removeAttribute('src')
  }
  currentTime.value = 0
  duration.value = 0
  if (shuffle.value) buildShuffleOrder()
  if (options.autoplay && tracks.length > 0) {
    playAt(shuffle.value ? shuffleOrder[0] : 0)
  }
}

/** Play a list, optionally shuffled, starting from the first track. */
function playList(files, { context: ctx = null, shuffled = false } = {}) {
  const tracks = (files || []).map(toTrack)
  if (!tracks.length) return
  playGeneration += 1
  detachChunks()
  shuffle.value = shuffled
  playlist.value = tracks
  context.value = ctx
  currentIndex.value = -1
  if (shuffled) {
    buildShuffleOrder()
    playAt(shuffleOrder[0])
  } else {
    playAt(0)
  }
}

function insertTracks(files, position) {
  const tracks = (files || []).map(toTrack)
  if (!tracks.length) return
  if (!playlist.value.length) {
    setPlaylist(tracks, { autoplay: true, context: null })
    return
  }
  const list = playlist.value.slice()
  list.splice(position, 0, ...tracks)
  playlist.value = list
  if (currentIndex.value >= position) currentIndex.value += tracks.length
  if (shuffle.value) {
    // Keep the shuffled path, slotting the new tracks in right after
    // the current one when asked to play them next.
    shuffleOrder = shuffleOrder.map((i) =>
      i >= position ? i + tracks.length : i
    )
    const added = tracks.map((_, k) => position + k)
    const at =
      position === currentIndex.value + 1 ? shufflePos + 1 : shuffleOrder.length
    shuffleOrder.splice(at, 0, ...added)
    shuffleVersion.value += 1
  }
}

/** Add to the end of the queue. */
function enqueue(files) {
  insertTracks(files, playlist.value.length)
}

/** Add right after the current track. */
function playNext(files) {
  insertTracks(files, currentIndex.value + 1)
}

function moveTrack(from, to) {
  const list = playlist.value.slice()
  if (from === to || from < 0 || to < 0) return
  if (from >= list.length || to >= list.length) return
  const [track] = list.splice(from, 1)
  list.splice(to, 0, track)
  playlist.value = list
  const current = currentIndex.value
  if (current === from) currentIndex.value = to
  else if (from < current && to >= current) currentIndex.value = current - 1
  else if (from > current && to <= current) currentIndex.value = current + 1
  if (shuffle.value) buildShuffleOrder()
}

function removeAt(index) {
  if (index < 0 || index >= playlist.value.length) return
  const list = playlist.value.slice()
  list.splice(index, 1)
  const wasCurrent = index === currentIndex.value
  playlist.value = list
  if (index < currentIndex.value) currentIndex.value -= 1
  if (shuffle.value) buildShuffleOrder()
  if (wasCurrent) {
    if (!list.length) {
      stop()
    } else {
      playAt(Math.min(index, list.length - 1))
    }
  }
}

/** Drop everything after the current track. */
function clearUpcoming() {
  if (currentIndex.value < 0) {
    stop()
    return
  }
  playlist.value = [playlist.value[currentIndex.value]]
  currentIndex.value = 0
  if (shuffle.value) buildShuffleOrder()
}

/** Remove files that no longer exist (deleted from the library). */
function forgetFiles(files) {
  const gone = new Set(files)
  for (let i = playlist.value.length - 1; i >= 0; i--) {
    if (gone.has(playlist.value[i].file)) removeAt(i)
  }
}

/** Refresh queued track details (e.g. tags) from the library. */
function refreshTracks(byFile) {
  let changed = false
  const list = playlist.value.map((track) => {
    const fresh = byFile.get(track.file)
    if (fresh && fresh !== track) {
      changed = true
      return fresh
    }
    return track
  })
  if (changed) playlist.value = list
}

function stop() {
  playGeneration += 1
  detachChunks()
  pause()
  if (audio) audio.removeAttribute('src')
  playlist.value = []
  currentIndex.value = -1
  currentTime.value = 0
  duration.value = 0
  context.value = null
}

// ── Transport ────────────────────────────────────────────────────────
function playAt(index) {
  if (index < 0 || index >= playlist.value.length) return
  playGeneration += 1
  detachChunks()
  const a = ensureAudio()
  currentIndex.value = index
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const pos = shuffleOrder.indexOf(index)
    if (pos >= 0) shufflePos = pos
    shuffleVersion.value += 1
  }
  playError.value = ''
  if (needsStreamUrl(playlist.value[index])) {
    void playUnresolved(index, playGeneration)
    return
  }
  startAudio(a, index)
}

// Bumped by every queue change, so async resolves never land on a track
// that moved on (or left the queue) while the network answered.
let playGeneration = 0

// The active piece-by-piece session of the current stream track, if any
// (see model/chunked.js). Dropped on every track change, stop or queue.
let chunkSession = null

function detachChunks() {
  if (chunkSession) {
    try {
      chunkSession.detach()
    } catch {
      // Already torn down.
    }
    chunkSession = null
  }
}

// Unresolved stream failures in a row before giving up on the queue
// (reset by any success) - a run of unresolvable tracks skips itself
// instead of stalling the player forever.
const MAX_RESOLVE_FAILURES = 3
let resolveFailures = 0

/** A streamed track whose fresh URL isn't known yet. */
function needsStreamUrl(track) {
  return !!track?.stream && !track.url
}

function startAudio(a, index) {
  a.src = playlist.value[index].url
  a.currentTime = 0
  // A track change doesn't reliably keep the rate in every browser — a
  // podcast episode played at 1.5x shouldn't drop back to 1x on next.
  a.playbackRate = playbackRate.value
  currentTime.value = 0
  startPlayback(a)
  // One track ahead: the next stream resolves while this one plays, so
  // advancing into it (or the track ending) never waits on the network.
  prefetchNext()
}

/** Play an unstored stream track, piece by piece - or skip past it. */
async function playUnresolved(index, gen) {
  let entry = playlist.value[index]
  const audio = ensureAudio()
  resolving.value = entry
  isBuffering.value = true
  playError.value = ''
  currentTime.value = 0
  duration.value = Number(entry.duration) || 0
  // Identity by content, not by object: reads through the reactive
  // playlist come back wrapped in proxies, so `!==` against a stored
  // raw object is always true after the first rewrite below.
  const stale = () =>
    gen !== playGeneration ||
    currentIndex.value !== index ||
    trackIdentity(playlist.value[index]) !== trackIdentity(entry)
  const done = () => {
    if (
      resolving.value &&
      trackIdentity(resolving.value) === trackIdentity(entry)
    ) {
      resolving.value = null
    }
  }
  let videoId = ''
  try {
    videoId = await ensureVideoId(entry)
  } catch {
    videoId = ''
  }
  if (stale()) {
    done()
    return
  }
  if (!videoId) {
    done()
    skipUnresolved()
    return
  }
  entry = { ...entry, video_id: videoId }
  playlist.value[index] = entry
  if (chunkingSupported()) {
    const session = createChunkSession(audio, {
      videoId,
      total: entry.duration || 0,
    })
    chunkSession = session
    resumeEqualizer()
    try {
      await session.start()
    } catch {
      if (stale()) {
        done()
        return
      }
      done()
      skipUnresolved()
      return
    }
    if (stale()) {
      if (chunkSession === session) detachChunks()
      done()
      return
    }
    if (!entry.duration && session.total > 0) {
      entry = { ...entry, duration: session.total }
      playlist.value[index] = entry
    }
    resolveFailures = 0
    done()
    prefetchNext()
    return
  }
  let url = ''
  let fetchedDuration = 0
  try {
    ;({ url, duration: fetchedDuration } = await resolveTrackUrl({
      ...entry,
      youtube_id: videoId,
    }))
  } catch {
    url = ''
  }
  if (stale()) {
    done()
    return
  }
  if (!url) {
    done()
    skipUnresolved()
    return
  }
  resolveFailures = 0
  playlist.value[index] = {
    ...entry,
    url,
    duration: entry.duration || fetchedDuration,
  }
  done()
  startAudio(ensureAudio(), index)
}

function skipUnresolved() {
  resolveFailures += 1
  if (resolveFailures >= MAX_RESOLVE_FAILURES) {
    resolveFailures = 0
    playError.value = 'unplayable'
    isBuffering.value = false
    pause()
    return
  }
  next()
}

/** Prepare the next unstored track while this one plays, one ahead. */
function prefetchNext() {
  const upcoming = nextIndex()
  if (upcoming < 0) return
  const track = playlist.value[upcoming]
  if (!needsStreamUrl(track)) return
  const list = playlist.value
  if (chunkingSupported()) {
    // Its video id, length and first piece: advancing starts instantly.
    prepareTrack(track).then(
      (ready) => {
        if (!ready) return
        if (playlist.value === list && playlist.value[upcoming] === track) {
          playlist.value[upcoming] = {
            ...track,
            video_id: ready.videoId,
            duration: track.duration || ready.duration,
          }
        }
      },
      () => {
        // Silent: advancing into it prepares again, with an error then.
      }
    )
    return
  }
  resolveTrackUrl(track).then(
    ({ url, duration }) => {
      // Another queue took its place meanwhile: leave it alone.
      if (playlist.value === list && playlist.value[upcoming] === track) {
        playlist.value[upcoming] = {
          ...track,
          url,
          duration: track.duration || duration,
        }
      }
    },
    () => {
      // Silent: advancing into it resolves again, with an error then.
    }
  )
}

/** Safety net: a fully-appended stream that never fired `ended`. */
let chunkEndStallTicks = 0

function watchChunkEnd(audio) {
  if (!chunkSession || !isPlaying.value) {
    chunkEndStallTicks = 0
    return
  }
  let end = 0
  let ended = false
  try {
    end = chunkSession.bufferedEnd()
    ended = chunkSession.isEnded()
  } catch {
    return
  }
  if (audio.currentTime >= end - 0.15 && ended) {
    chunkEndStallTicks += 1
    if (chunkEndStallTicks >= 8) {
      chunkEndStallTicks = 0
      onEnded()
    }
  } else {
    chunkEndStallTicks = 0
  }
}

function startPlayback(a) {
  resumeEqualizer()
  a.play().catch(() => {})
}

function play() {
  if (playlist.value.length === 0) return
  const a = ensureAudio()
  if (currentIndex.value < 0) {
    playAt(shuffle.value && shuffleOrder.length ? shuffleOrder[0] : 0)
    return
  }
  if (!a.src) {
    // Paused mid-resolve (or before it started): go through playAt so an
    // unstored track resolves instead of loading an empty src.
    if (needsStreamUrl(playlist.value[currentIndex.value])) {
      playAt(currentIndex.value)
      return
    }
    a.src = playlist.value[currentIndex.value].url
  }
  startPlayback(a)
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
  const track = playlist.value[currentIndex.value]
  // A streamed track may not have the target part loaded yet: fetch its
  // piece first, then jump. Buffered targets jump at once, inside.
  if (chunkSession && track?.stream && !track.url) {
    const max = duration.value || seconds
    const clamped = Math.max(0, Math.min(max, seconds))
    isBuffering.value = true
    chunkSession
      .seekTo(clamped)
      .catch(() => {
        // Keep the old position; the fetch-ahead recovers.
      })
      .finally(() => {
        if (isPlaying.value) startPlayback(a)
        else isBuffering.value = false
      })
    return
  }
  const max = duration.value || 0
  const clamped = Math.max(0, Math.min(max, seconds))
  a.currentTime = clamped
  currentTime.value = clamped
}

function seekRatio(ratio) {
  if (!duration.value) return
  seek(duration.value * Math.max(0, Math.min(1, ratio)))
}

function seekBy(delta) {
  seek(currentTime.value + delta)
}

function setVolume(v) {
  const clamped = Math.max(0, Math.min(1, v))
  volume.value = clamped
  if (audio) audio.volume = clamped
  try {
    storage()?.setItem(VOLUME_KEY, String(clamped))
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

function setPlaybackRate(rate) {
  const clamped = Math.max(0.5, Math.min(3, rate))
  playbackRate.value = clamped
  if (audio) audio.playbackRate = clamped
  try {
    storage()?.setItem(RATE_KEY, String(clamped))
  } catch {
    // ignore
  }
}

function nextIndex() {
  if (playlist.value.length === 0) return -1
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const nextPos = shufflePos + 1
    if (nextPos >= shuffleOrder.length) {
      return repeatMode.value === 'all' ? shuffleOrder[0] : -1
    }
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
  if (sleepAt.value === 'track') {
    setSleepTimer(null)
    pause()
    return
  }
  if (repeatMode.value === 'one') {
    seek(0)
    if (audio) startPlayback(audio)
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

// ── Sleep timer ──────────────────────────────────────────────────────
/** `minutes` (number), `'track'` (end of this track) or null (off). */
function setSleepTimer(minutes) {
  if (sleepTimer) {
    clearTimeout(sleepTimer)
    sleepTimer = null
  }
  if (minutes === 'track') {
    sleepAt.value = 'track'
    return
  }
  if (!minutes) {
    sleepAt.value = null
    return
  }
  sleepAt.value = Date.now() + minutes * 60 * 1000
  sleepTimer = setTimeout(
    () => {
      pause()
      sleepAt.value = null
      sleepTimer = null
    },
    minutes * 60 * 1000
  )
}

// ── Derived state ────────────────────────────────────────────────────
const currentTrack = computed(() =>
  currentIndex.value >= 0 && currentIndex.value < playlist.value.length
    ? playlist.value[currentIndex.value]
    : null
)

const progressPct = computed(() =>
  duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
)

/** Upcoming tracks, in the order they'll play: `[{ track, index }]`. */
const upcoming = computed(() => {
  const list = playlist.value
  // Reading these keeps the computed in step with shuffle/index changes.
  const current = currentIndex.value
  shuffleVersion.value
  if (shuffle.value && shuffleOrder.length === list.length) {
    return shuffleOrder
      .slice(shufflePos + 1)
      .map((index) => ({ track: list[index], index }))
  }
  return list
    .slice(current + 1)
    .map((track, k) => ({ track, index: current + 1 + k }))
})

// ── Media Session (lock screen / headset / keyboard media keys) ──────
function updateMediaSession(track) {
  if (typeof navigator === 'undefined' || !('mediaSession' in navigator)) {
    return
  }
  const session = navigator.mediaSession
  if (!track) {
    session.metadata = null
    return
  }
  if (typeof MediaMetadata !== 'undefined') {
    const origin = typeof location !== 'undefined' ? location.origin : ''
    const cover = String(track.cover || '')
    const artwork =
      track.hasCover && cover
        ? [
            {
              src: cover.startsWith('http') ? cover : `${origin}${cover}`,
              sizes: '512x512',
            },
          ]
        : []
    session.metadata = new MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: track.album || '',
      artwork,
    })
  }
  const handlers = {
    play,
    pause,
    previoustrack: prev,
    nexttrack: next,
    seekbackward: () => seekBy(-10),
    seekforward: () => seekBy(10),
    seekto: (details) => seek(details.seekTime || 0),
    stop: pause,
  }
  for (const [action, handler] of Object.entries(handlers)) {
    try {
      session.setActionHandler(action, handler)
    } catch {
      // Unsupported action on this browser.
    }
  }
}

watch(currentTrack, (track) => updateMediaSession(track))
watch(isPlaying, (playing) => {
  if (typeof navigator !== 'undefined' && 'mediaSession' in navigator) {
    navigator.mediaSession.playbackState = playing ? 'playing' : 'paused'
  }
})

// ── Persist the session across reloads ───────────────────────────────
function saveSession() {
  const store = storage()
  if (!store) return
  // A stream's URL expires within hours: persisting it would restore a
  // dead track, so a queue holding one is never saved at all.
  if (
    !playlist.value.length ||
    playlist.value.length > MAX_PERSISTED_TRACKS ||
    playlist.value.some((track) => track?.stream)
  ) {
    store.removeItem(SESSION_KEY)
    return
  }
  try {
    store.setItem(
      SESSION_KEY,
      JSON.stringify({
        tracks: playlist.value,
        index: currentIndex.value,
        time: Math.floor(currentTime.value),
        context: context.value,
        shuffle: shuffle.value,
        repeat: repeatMode.value,
      })
    )
  } catch {
    // Quota exceeded — keep playing, just don't persist.
  }
}

function restoreSession() {
  const raw = storage()?.getItem(SESSION_KEY)
  if (!raw) return
  try {
    const saved = JSON.parse(raw)
    if (!Array.isArray(saved.tracks) || !saved.tracks.length) return
    playlist.value = saved.tracks
    currentIndex.value = Math.min(saved.index ?? -1, saved.tracks.length - 1)
    context.value = saved.context || null
    repeatMode.value = saved.repeat || 'off'
    shuffle.value = !!saved.shuffle
    if (shuffle.value) buildShuffleOrder()
    const track = currentTrack.value
    if (track) {
      const a = ensureAudio()
      restoreTime = saved.time || 0
      currentTime.value = restoreTime
      a.src = track.url
    }
  } catch {
    storage()?.removeItem(SESSION_KEY)
  }
}

if (typeof window !== 'undefined' && typeof Audio !== 'undefined') {
  restoreSession()
  watch([playlist, currentIndex, context, shuffle, repeatMode], saveSession)
  window.addEventListener('pagehide', saveSession)
  setInterval(() => {
    if (isPlaying.value) saveSession()
  }, 5000)
}

// ── Public API ───────────────────────────────────────────────────────
export function formatTime(seconds) {
  if (!isFinite(seconds) || seconds < 0) return '0:00'
  const total = Math.floor(seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function trackInfoFromFile(file) {
  return normalizeTrack(file)
}

export function usePlayer() {
  return {
    playlist,
    currentIndex,
    currentTrack,
    upcoming,
    context,
    isPlaying,
    isBuffering,
    playError,
    currentTime,
    duration,
    progressPct,
    volume,
    isMuted,
    playbackRate,
    repeatMode,
    shuffle,
    sleepAt,
    resolving,
    setPlaylist,
    playList,
    enqueue,
    playNext,
    moveTrack,
    removeAt,
    clearUpcoming,
    forgetFiles,
    refreshTracks,
    stop,
    playAt,
    play,
    pause,
    toggle,
    seek,
    seekRatio,
    seekBy,
    setVolume,
    toggleMute,
    setPlaybackRate,
    next,
    prev,
    setRepeat,
    cycleRepeat,
    setShuffle,
    toggleShuffle,
    setSleepTimer,
  }
}
