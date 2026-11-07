// Technical validation only: never include URLs, session ids, titles or raw errors.
export function createDjDiagnostics({
  enabled,
  media,
  position,
  now = () => performance.now(),
  report = (value) => console.warn('DJ validation ' + JSON.stringify(value)),
}) {
  let lastReceipt = -Infinity,
    lastError = -Infinity,
    resets = -1,
    transport = {}
  const events = { waiting: 0, seeking: 0, pause: 0 }
  const number = (value) =>
    Number.isFinite(value) ? Math.round(value * 1000) / 1000 : 0
  const code = (value) =>
    /^[a-zA-Z][a-zA-Z0-9]{0,47}$/.test(value) ? value : 'unknown'
  function emit(kind, extra) {
    let buffered = 0
    const time = media.currentTime
    for (let i = 0; i < (media.buffered?.length || 0); i++)
      if (media.buffered.start(i) <= time && time <= media.buffered.end(i))
        buffered = media.buffered.end(i) - time
    report({
      kind,
      audio_seconds: number(time),
      mix_seconds: number(position()),
      playback_rate: number(media.playbackRate),
      paused: media.paused === true,
      seeking: media.seeking === true,
      ready_state: number(media.readyState),
      buffered_seconds: number(buffered),
      events: { ...events },
      ...transport,
      ...extra,
    })
  }
  return {
    stream(value) {
      if (!enabled()) return
      transport = {
        latency_seconds: number(value.latency_seconds),
        load_ms: number(value.load_ms),
      }
      if (value.kind !== 'error' || now() - lastError < 1000) return
      lastError = now()
      emit('hls', {
        type: code(value.error?.type),
        detail: code(value.error?.detail),
        fatal: value.error?.fatal === true,
        http_status: number(value.error?.http_status),
      })
    },
    interruption(type) {
      if (!enabled() || !Object.hasOwn(events, type)) return
      events[type]++
      emit('event', { event: type })
    },
    receipt(value, sentAt) {
      if (!enabled()) return
      const count = number(value.total_interruptions)
      if (count === resets && now() - lastReceipt < 30000) return
      resets = count
      lastReceipt = now()
      const counts = {}
      for (const reason of [
        'paused',
        'client_event',
        'clock_gap',
        'no_progress',
        'clock_drift',
      ])
        counts[reason] = number(value.reset_counts?.[reason])
      emit('receipt', {
        rtt_ms: number(now() - sentAt),
        continuous_seconds: number(value.continuous_seconds),
        phase_error_seconds: number(value.clock_delta_seconds),
        reset_counts: counts,
      })
    },
  }
}
