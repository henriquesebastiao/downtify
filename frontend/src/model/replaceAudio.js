// Which track the "Replace audio" dialog is open for (one at a time, for
// the whole app - see ReplaceAudioDialog in AppShell).
import { ref } from 'vue'

const track = ref(null)

function open(next) {
  track.value = next
}

function close() {
  track.value = null
}

export function useReplaceAudio() {
  return { track, open, close }
}
