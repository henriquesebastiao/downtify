import { describe, expect, it } from 'vitest'
import { advancePlayhead, createPlayhead, reportTime } from '../lib/playhead.js'

// Simulates 60 fps frames with `timeupdate` reports every 250 ms, and
// returns the shown time at each frame.
function simulate({ seconds, start = 0, reportEvery = 250, playing = true }) {
  const playhead = createPlayhead(start, 0)
  const frames = []
  const frameMs = 1000 / 60
  let nextReport = reportEvery
  for (let now = frameMs; now <= seconds * 1000; now += frameMs) {
    if (now >= nextReport) {
      reportTime(playhead, start + (playing ? nextReport / 1000 : 0), now)
      nextReport += reportEvery
    }
    frames.push(
      advancePlayhead(playhead, { now, dt: frameMs / 1000, playing, max: 999 })
    )
  }
  return frames
}

describe('advancePlayhead', () => {
  it('moves a little every frame instead of in 250 ms steps', () => {
    const frames = simulate({ seconds: 3 })
    const steps = frames.slice(30).map((v, i, all) => (i ? v - all[i - 1] : 0))
    // Never still, never backwards, never a big jump.
    for (const step of steps.slice(1)) {
      expect(step).toBeGreaterThan(0)
      expect(step).toBeLessThan(0.05)
    }
  })

  it('keeps close to real playback time', () => {
    const frames = simulate({ seconds: 3 })
    const real = 3 - 1 / 60
    expect(Math.abs(frames.at(-1) - real)).toBeLessThan(0.3)
  })

  it('jumps straight to a seek', () => {
    const playhead = createPlayhead(10, 0)
    advancePlayhead(playhead, { now: 16, dt: 0.016, playing: true, max: 999 })
    reportTime(playhead, 120, 32)
    const shown = advancePlayhead(playhead, {
      now: 48,
      dt: 0.016,
      playing: true,
      max: 999,
    })
    expect(shown).toBeCloseTo(120.016, 2)
  })

  it('follows the reported time exactly when paused or dragging', () => {
    const playhead = createPlayhead(50, 0)
    reportTime(playhead, 42.5, 1000)
    expect(
      advancePlayhead(playhead, {
        now: 5000,
        dt: 0.016,
        playing: false,
        max: 999,
      })
    ).toBe(42.5)
  })

  it('never passes the end of the track', () => {
    const playhead = createPlayhead(99.9, 0)
    expect(
      advancePlayhead(playhead, {
        now: 5000,
        dt: 0.016,
        playing: true,
        max: 100,
      })
    ).toBe(100)
  })
})
