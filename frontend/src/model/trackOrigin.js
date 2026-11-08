// What the "Where it came from" dialog is open for (one at a time, for
// the whole app - see TrackOriginDialog in AppShell): a library track.
import { ref } from 'vue'

const target = ref(null)

function open(track) {
  if (!track?.file) return
  target.value = track
}

function close() {
  target.value = null
}

export function useTrackOrigin() {
  return { target, open, close }
}
