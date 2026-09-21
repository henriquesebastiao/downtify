// Podcast subscriptions: the shows list, and keeping an episode's resume
// position saved on the server while it plays — so closing the tab and
// reopening it (or picking up on another device) lands back where the
// listener left off. The episode list itself lives in the show page
// that's looking at it (see PodcastShowView.vue), not here.
import { ref, watch } from 'vue'

import API from '/src/model/api'
import { usePlayer } from '/src/model/player'
import { isNearlyDone } from '/src/lib/podcasts'

const shows = ref([])
const loaded = ref(false)

async function load() {
  try {
    const res = await API.listPodcastShows()
    shows.value = res.data || []
    loaded.value = true
  } catch {
    // Keep what is shown; the page that needs it retries on its own.
  }
}

async function subscribe(payload) {
  const res = await API.subscribePodcast(payload)
  shows.value = [...shows.value, res.data]
  return res.data
}

async function updateShow(show, changes) {
  const before = { ...show }
  Object.assign(show, changes)
  try {
    const res = await API.updatePodcastShow(show.id, changes)
    Object.assign(show, res.data)
    return true
  } catch {
    Object.assign(show, before)
    return false
  }
}

async function unsubscribe(show, { keepFiles = false } = {}) {
  await API.deletePodcastShow(show.id, keepFiles)
  shows.value = shows.value.filter((s) => s.id !== show.id)
}

function findShow(id) {
  return shows.value.find((s) => String(s.id) === String(id)) || null
}

// ── Resume position: saved every ~10s of real playback, and once more
// whenever playback pauses. Idempotent PUTs, so a missed or repeated
// tick never corrupts anything — worst case a few seconds are replayed.
const SAVE_EVERY_SECONDS = 10
let lastSavedAt = 0
let progressSyncStarted = false

function _savePosition(track, positionSeconds, durationSeconds) {
  if (!track?.podcastEpisodeId) return
  API.setPodcastPlayback(track.podcastEpisodeId, {
    position_seconds: positionSeconds,
    played: isNearlyDone(positionSeconds, durationSeconds) || undefined,
  }).catch(() => {
    // Best-effort — the next tick or the next pause tries again.
  })
}

function _startProgressSync() {
  if (progressSyncStarted) return
  progressSyncStarted = true
  const player = usePlayer()

  watch(player.currentTime, (seconds) => {
    const track = player.currentTrack.value
    if (!track?.isPodcast) return
    if (seconds - lastSavedAt < SAVE_EVERY_SECONDS && seconds > lastSavedAt) {
      return
    }
    lastSavedAt = seconds
    _savePosition(track, seconds, track.duration)
  })

  // A pause (including the moment before the queue advances to the
  // next track) is worth an immediate save rather than waiting out the
  // interval above.
  watch(player.isPlaying, (playing) => {
    const track = player.currentTrack.value
    if (playing || !track?.isPodcast) return
    _savePosition(track, player.currentTime.value, track.duration)
  })

  watch(player.currentTrack, () => {
    lastSavedAt = 0
  })
}

export function usePodcasts() {
  _startProgressSync()
  return {
    shows,
    loaded,
    load,
    subscribe,
    updateShow,
    unsubscribe,
    findShow,
  }
}
