// Plays the 30 s preview of a song that isn't downloaded yet, on its own row.
//
// Deliberately apart from the built-in player: its own <audio> element, no
// queue, no equalizer, no session saved, no Now playing. The row that asks
// for a preview shows the state (see TrackDownPlay); this only keeps one
// clip going at a time and stays out of the player's way - starting a clip
// pauses the player, and the player starting stops the clip.
import { ref, watch } from 'vue'

import { usePlayer } from '/src/model/player'
import { previewRatio, previewUrl } from '/src/lib/preview'

const player = usePlayer()

// `song_id` of the song whose clip is loaded ('' when none), and its state.
const activeId = ref('')
const isPlaying = ref(false)
const isLoading = ref(false)
// How far into the clip, 0 to 1.
const progress = ref(0)

let audio = null

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

/**
 * The row's play/pause: starts `song`'s clip, or pauses/resumes it when it
 * is already the one loaded. A clip of another song is replaced.
 */
function toggle(song) {
  const url = previewUrl(song)
  const id = String(song?.song_id || '')
  if (!url || !id) return
  const a = ensureAudio()
  if (activeId.value === id) {
    if (a.paused) run(a, id)
    else a.pause()
    return
  }
  if (player.isPlaying.value) player.pause()
  activeId.value = id
  progress.value = 0
  isLoading.value = true
  a.src = url
  run(a, id)
}

// The player starting (its own controls, the media keys, a downloaded row)
// ends the clip: two things playing at once is never wanted.
watch(player.isPlaying, (playing) => {
  if (playing) stop()
})

export function usePreview() {
  return { activeId, isPlaying, isLoading, progress, toggle, stop, stopFor }
}
