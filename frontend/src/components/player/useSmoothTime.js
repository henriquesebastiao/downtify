// A reactive playback time that glides between the browser's time
// reports (see lib/playhead.js), for progress bars outside the canvas.
import { onBeforeUnmount, ref, watch } from 'vue'
import { advancePlayhead, createPlayhead, reportTime } from '/src/lib/playhead'

/**
 * `source()` → reported time, `playing()` → whether to glide,
 * `max()` → duration. Returns a ref with the time to draw.
 */
export function useSmoothTime(source, playing, max) {
  const playhead = createPlayhead(source(), 0)
  const shown = ref(source())
  let frame = 0
  let last = 0

  function step(now) {
    frame = 0
    const dt = last ? Math.min(0.05, (now - last) / 1000) : 0
    last = now
    shown.value = advancePlayhead(playhead, {
      now,
      dt,
      playing: playing(),
      max: max(),
    })
    if (playing() && !document.hidden) frame = requestAnimationFrame(step)
    else last = 0
  }

  function schedule() {
    if (typeof window === 'undefined' || frame) return
    frame = requestAnimationFrame(step)
  }

  watch(source, (value) => {
    reportTime(playhead, value, performance.now())
    schedule()
  })
  watch([playing, max], schedule)

  function onVisibility() {
    if (!document.hidden) schedule()
  }
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', onVisibility)
    reportTime(playhead, source(), performance.now())
    schedule()
  }
  onBeforeUnmount(() => {
    cancelAnimationFrame(frame)
    document.removeEventListener('visibilitychange', onVisibility)
  })

  return shown
}
