import { watch } from 'vue'
import { musicAI } from '/src/model/musicAI'
import { ListenedTime } from '/src/lib/listenedTime'

export function attachMusicAiListening(audio, currentTrack) {
  const account = musicAI.account
  let active = null
  let terminal = false
  const handlers = []
  const on = (event, handler) => {
    handlers.push([event, handler])
    audio.addEventListener(event, handler)
  }
  const revision = () => musicAI.capabilities.value?.profile_revision || 0
  const enabled = () =>
    account.value &&
    musicAI.capabilities.value?.features.personalization === true
  function publish(outcome) {
    if (!active || !enabled() || active.owner !== account.value || active.generation !== revision()) return
    const event = {
      event_id: active.id,
      library_file: active.file,
      seconds: active.time.seconds,
      sequence: ++active.sequence,
      generation: active.generation,
      outcome,
    }
    active.sentAt = performance.now()
    void musicAI.listen(event).catch(() => {})
  }
  function sample() {
    if (!enabled() || terminal) {
      active = null
      return
    }
    const track = currentTrack()
    if (!track?.file || track.stream || track.episode || track.podcast) return
    if (active?.file !== track.file || active.generation !== revision() || active.djOccurrence !== track.djOccurrence) {
      publish(active?.djSession && active.djSession === track.djSession ? 'pause' : 'skip')
      const id = Array.from(
        crypto.getRandomValues(new Uint8Array(16)),
        (value) => value.toString(16).padStart(2, '0')
      ).join('')
      active = {
        file: track.file,
        djSession: track.djSession,
        djOccurrence: track.djOccurrence,
        id,
        owner: account.value,
        generation: revision(),
        sequence: 0,
        time: new ListenedTime(),
        sentAt: performance.now(),
      }
    }
    active.time.sample(
      audio.currentTime,
      performance.now(),
      !audio.paused && !audio.seeking
    )
    if (performance.now() - active.sentAt >= 20000) publish('pause')
  }
  on('timeupdate', sample)
  on('playing', () => {
    terminal = false
    void musicAI.refresh()
    sample()
  })
  on('pause', () => {
    sample()
    publish('pause')
  })
  on('ended', () => {
    sample()
    publish('complete')
    active = null
    terminal = true
  })
  on('error', () => {
    publish('error')
    active = null
    terminal = true
  })
  on('loadstart', () => {
    terminal = false
    if (active) {
      publish('skip')
      active = null
    }
  })
  const stopAccount = watch(
    () => account.value,
    () => {
      active = null
    }
  )
  const stopFeatures = watch(
    () => musicAI.capabilities.value?.features.personalization,
    (value) => {
      if (!value) active = null
    }
  )
  return () => {
    publish('pause')
    active = null
    stopAccount()
    stopFeatures()
    for (const [event, handler] of handlers) audio.removeEventListener(event, handler)
  }
}
