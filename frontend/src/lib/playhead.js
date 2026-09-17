// Smooth playhead: the browser reports playback time only a few times a
// second (`timeupdate`), so a thumb that follows it jumps in steps.
// Between reports, predict the time from the clock and glide towards it.

// Further than this from the prediction (a seek, a new track): jump.
const SNAP_SECONDS = 1
// How quickly the shown time closes the gap to the prediction, per second.
const FOLLOW_RATE = 10
// Tiny backward corrections are held instead of drawn as a step back.
const HOLD_SECONDS = 0.35

export function createPlayhead(value = 0, now = 0) {
  return { shown: value, value, at: now }
}

/** Records a reported playback time. */
export function reportTime(playhead, value, now) {
  playhead.value = value
  playhead.at = now
}

/**
 * Moves `playhead.shown` for a frame at `now` ms, `dt` seconds after the
 * previous one, and returns it. When not playing (paused, dragging) the
 * shown time is the reported one.
 */
export function advancePlayhead(playhead, { now, dt, playing, max }) {
  if (!playing) {
    playhead.shown = playhead.value
  } else {
    const predicted = playhead.value + (now - playhead.at) / 1000
    const gap = predicted - playhead.shown
    if (Math.abs(gap) > SNAP_SECONDS) playhead.shown = predicted
    else if (gap > 0) playhead.shown += gap * Math.min(1, dt * FOLLOW_RATE)
    else if (gap < -HOLD_SECONDS) playhead.shown = predicted
  }
  playhead.shown = Math.max(0, Math.min(max, playhead.shown))
  return playhead.shown
}
