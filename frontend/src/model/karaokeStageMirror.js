// The projected karaoke window's copy of the player: read-only state, kept
// up to date by the Downtify window that opened it. Must not import the
// player, which would start a second one here.
import { ref } from 'vue'

import {
  STAGE_PING_MS,
  STAGE_TIMEOUT_MS,
  stageChannelName,
} from '/src/lib/karaokeStage'

export function connectToHost(id) {
  const currentTrack = ref(null)
  const nextTrack = ref(null)
  const currentTime = ref(0)
  const isPlaying = ref(false)
  const channel = new BroadcastChannel(stageChannelName(id))
  let lastHeard = 0

  channel.onmessage = ({ data }) => {
    if (data?.type !== 'state') return
    lastHeard = Date.now()
    currentTrack.value = data.track
    nextTrack.value = data.next
    currentTime.value = data.time
    isPlaying.value = data.playing
  }

  function ping() {
    channel.postMessage({ type: 'ping' })
    if (Date.now() - lastHeard <= STAGE_TIMEOUT_MS) return
    // The Downtify window is gone, and the music with it.
    currentTrack.value = null
    nextTrack.value = null
    isPlaying.value = false
  }

  function sayBye() {
    channel.postMessage({ type: 'bye' })
  }

  ping()
  const timer = setInterval(ping, STAGE_PING_MS)
  window.addEventListener('pagehide', sayBye)

  function stop() {
    clearInterval(timer)
    window.removeEventListener('pagehide', sayBye)
    channel.close()
  }

  return { currentTrack, nextTrack, currentTime, isPlaying, stop }
}
