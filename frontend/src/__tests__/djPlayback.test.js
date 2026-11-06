import { describe, expect, it } from 'vitest'
import { isPlaybackInterruption } from '../model/djPlayback'

describe('continuous DJ playback evidence', () => {
  it('keeps a buffered network stall separate from an audible underrun', () => {
    expect(isPlaybackInterruption('stalled', { paused: false, readyState: 4 })).toBe(false)
    expect(isPlaybackInterruption('stalled', { paused: false, readyState: 3 })).toBe(false)
    expect(isPlaybackInterruption('stalled', { paused: false, readyState: 2 })).toBe(true)
    expect(isPlaybackInterruption('stalled', { paused: true, readyState: 2 })).toBe(false)
  })
  it('resets evidence on an actual wait, seek or pause, and ignores ordinary progress', () => {
    for (const event of ['waiting', 'seeking', 'pause']) expect(isPlaybackInterruption(event, {})).toBe(true)
    expect(isPlaybackInterruption('timeupdate', {})).toBe(false)
  })
})
