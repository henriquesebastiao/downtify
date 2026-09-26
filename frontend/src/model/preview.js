// Plays the 30 s preview of a song that isn't downloaded yet, on its own row.
//
// Deliberately apart from the built-in player: its own <audio> element, no
// queue, no equalizer, no session saved, no Now playing. The row that asks
// for a preview shows the state (see useSongPlay); this only keeps one
// clip going at a time and stays out of the player's way - starting a clip
// pauses the player, and the player starting stops the clip.
//
// A Spotify song brings its own clip (`preview_url`). Any other song - a
// YouTube Music result, a long playlist's later tracks - is looked up on
// Deezer the first time it's asked for (GET /api/preview); the answer is
// remembered for the session, and a song Deezer has nothing for stops
// offering a preview.
import { ref, shallowRef, watch } from 'vue'

import API from '/src/model/api'
import { usePlayer } from '/src/model/player'
import {
  previewKey,
  previewLookup,
  previewRatio,
  previewUrl,
} from '/src/lib/preview'

const player = usePlayer()

// `song_id` of the song whose clip is loaded ('' when none), and its state.
const activeId = ref('')
const isPlaying = ref(false)
const isLoading = ref(false)
// How far into the clip, 0 to 1.
const progress = ref(0)

let audio = null
// Clips looked up on Deezer, by previewKey: the URL, or '' for none.
const looked = new Map()
// Songs known to have no clip at all (reactive, so their rows update).
const unavailable = shallowRef(new Set())

/** Whether `song` has a clip, or might have one worth looking up. */
function canPreview(song) {
  if (previewUrl(song)) return true
  const key = previewKey(song)
  return Boolean(key && previewLookup(song) && !unavailable.value.has(key))
}

async function lookUp(song) {
  const key = previewKey(song)
  if (looked.has(key)) return looked.get(key)
  const lookup = previewLookup(song)
  if (!lookup) return ''
  // A failed request isn't remembered: the next tap asks again.
  const res = await API.findPreview(lookup)
  const url = previewUrl({ preview_url: res.data?.preview_url })
  looked.set(key, url)
  if (!url) unavailable.value = new Set([...unavailable.value, key])
  return url
}

function ensureAudio() {
  if (audio) return audio
  audio = new Audio()
  audio.addEventListener('timeupdate', () => {
    progress.value = previewRatio(audio.currentTime, audio.duration)
  })
  audio.addEventListener('play', () => {
    isPlaying.value = true
  })
  audio.addEventListener('pause', () => {
    isPlaying.value = false
  })
  audio.addEventListener('waiting', () => {
    isLoading.value = true
  })
  audio.addEventListener('playing', () => {
    isLoading.value = false
  })
  // Back to the row's idle look at the end, and when the clip can't play.
  audio.addEventListener('ended', stop)
  audio.addEventListener('error', stop)
  return audio
}

function stop() {
  if (audio) {
    audio.pause()
    audio.removeAttribute('src')
    audio.load?.()
  }
  activeId.value = ''
  isPlaying.value = false
  isLoading.value = false
  progress.value = 0
}

/** Stop the clip when it is the one of `id` (a row going away). */
function stopFor(id) {
  if (activeId.value === String(id)) stop()
}

function run(a, id) {
  // The player's level, so a clip isn't louder than the music.
  a.volume = player.volume.value
  a.muted = player.isMuted.value
  const started = a.play()
  // A rejected play() (autoplay policy, or a new clip taking over) only
  // resets this row - not one that has started since.
  started?.catch?.(() => {
    if (activeId.value === id) stop()
  })
}

function start(a, id, url) {
  a.src = url
  run(a, id)
}

async function startLookedUp(song, a, id) {
  let url = ''
  try {
    url = await lookUp(song)
  } catch {
    url = ''
  }
  // Another row (or the player) took over while this was looked up.
  if (activeId.value !== id) return true
  if (!url) {
    stop()
    return false
  }
  start(a, id, url)
  return true
}

/**
 * The row's play/pause: starts `song`'s clip, or pauses/resumes it when it
 * is already the one loaded. A clip of another song is replaced.
 *
 * A song with its own clip starts right away; one that has to be looked up
 * returns a promise, resolving `false` when it turned out to have no clip
 * (or the lookup failed), so the row can say so.
 */
function toggle(song) {
  const id = previewKey(song)
  if (!id || !canPreview(song)) return false
  const a = ensureAudio()
  if (activeId.value === id) {
    if (!a.src) return true // still being looked up
    if (a.paused) run(a, id)
    else a.pause()
    return true
  }
  if (player.isPlaying.value) player.pause()
  if (activeId.value) stop()
  activeId.value = id
  progress.value = 0
  isLoading.value = true
  const own = previewUrl(song)
  if (own) {
    start(a, id, own)
    return true
  }
  return startLookedUp(song, a, id)
}

// The player starting (its own controls, the media keys, a downloaded row)
// ends the clip: two things playing at once is never wanted.
watch(player.isPlaying, (playing) => {
  if (playing) stop()
})

export function usePreview() {
  return {
    activeId,
    isPlaying,
    isLoading,
    progress,
    unavailable,
    canPreview,
    toggle,
    stop,
    stopFor,
  }
}
