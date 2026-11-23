// The thin bar at the top of the window while a page is on its way (its
// code is loaded on demand). A pure timer machine, so it can be tested;
// components/shell/RouteProgress.vue draws it.

/** One step of the bar: a part of what is left, so it slows near `cap`. */
export function trickle(value, cap = 0.9, rate = 0.15) {
  return value + (cap - value) * rate
}

/**
 * `onChange({ visible, value })` is called whenever the bar changes. A page
 * that comes within `delay` ms never shows the bar at all.
 */
export function createRouteProgress({
  onChange,
  delay = 150,
  step = 200,
  hold = 260,
  // Longer than the fade-out, so the rewind is never seen.
  rewind = 400,
  timers = globalThis,
} = {}) {
  let state = { visible: false, value: 0 }
  let waiting = null
  let ticking = null
  let hiding = null

  function set(next) {
    state = { ...state, ...next }
    onChange?.(state)
  }

  function stopTimers() {
    timers.clearTimeout(waiting)
    timers.clearInterval(ticking)
    waiting = null
    ticking = null
  }

  function start() {
    if (waiting || ticking) return
    if (hiding) {
      // Still fading from the last page: start the new bar from nothing.
      timers.clearTimeout(hiding)
      hiding = null
      set({ visible: false, value: 0 })
    }
    waiting = timers.setTimeout(() => {
      waiting = null
      set({ visible: true, value: 0.1 })
      ticking = timers.setInterval(
        () => set({ value: trickle(state.value) }),
        step
      )
    }, delay)
  }

  function done() {
    const shown = Boolean(ticking)
    stopTimers()
    if (!shown) return
    // Fill it, let that be seen, then fade it out and rewind it unseen.
    set({ value: 1 })
    hiding = timers.setTimeout(() => {
      set({ visible: false })
      hiding = timers.setTimeout(() => {
        hiding = null
        set({ value: 0 })
      }, rewind)
    }, hold)
  }

  return {
    start,
    done,
    get state() {
      return state
    },
  }
}
