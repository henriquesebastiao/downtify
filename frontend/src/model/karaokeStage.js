// The Downtify window's side of the projected karaoke window: it keeps the
// audio and tells the stage what is playing (see lib/karaokeStage.js).
import { ref, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'

import config from '/src/config'
import { usePlayer } from '/src/model/player'
import {
  STAGE_TIMEOUT_MS,
  stageChannelName,
  stagePath,
  stageState,
  stageWindowName,
} from '/src/lib/karaokeStage'

// Per tab, and kept across a reload: an open stage finds its tab again,
// and a second Downtify tab doesn't answer for this one.
const HOST_KEY = 'downtify-karaoke-host'
const WINDOW_FEATURES = 'popup,width=1280,height=720'

const connected = ref(false)
let channel = null
let dropTimer = null
let stageWindow = null

function session() {
  try {
    return typeof sessionStorage !== 'undefined' ? sessionStorage : null
  } catch {
    return null
  }
}

function hostId() {
  const store = session()
  let id = store?.getItem(HOST_KEY)
  if (!id) {
    id = uuidv4()
    store?.setItem(HOST_KEY, id)
  }
  return id
}

function disconnect() {
  clearTimeout(dropTimer)
  connected.value = false
}

function attach(id) {
  if (channel) return
  const player = usePlayer()
  const nextTrack = () => player.upcoming.value[0]?.track
  channel = new BroadcastChannel(stageChannelName(id))

  function publish() {
    channel.postMessage(
      stageState({
        track: player.currentTrack.value,
        next: nextTrack(),
        time: player.currentTime.value,
        playing: player.isPlaying.value,
      })
    )
  }

  channel.onmessage = ({ data }) => {
    if (data?.type === 'bye') disconnect()
    if (data?.type !== 'ping') return
    connected.value = true
    clearTimeout(dropTimer)
    dropTimer = setTimeout(disconnect, STAGE_TIMEOUT_MS)
    publish()
  }

  watch(
    [player.currentTrack, nextTrack, player.currentTime, player.isPlaying],
    () => {
      if (connected.value) publish()
    }
  )
}

/** After a reload: pick up a stage this tab had already opened. */
function resume() {
  const id = session()?.getItem(HOST_KEY)
  if (id) attach(id)
}

/** Open the stage, or bring it forward. False if the browser blocked it. */
function open() {
  const id = hostId()
  attach(id)
  if (connected.value && stageWindow && !stageWindow.closed) {
    stageWindow.focus()
    return true
  }
  stageWindow = window.open(
    stagePath(config.BASEURL, id),
    stageWindowName(id),
    WINDOW_FEATURES
  )
  if (!stageWindow) return false
  stageWindow.focus()
  return true
}

export function useKaraokeStage() {
  return { connected, open, resume }
}
