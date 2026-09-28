import { describe, expect, it } from 'vitest'
import { canReplace, lengthDiff, sameLength } from '../lib/replaceAudio.js'

describe('replace audio helpers', () => {
  it('writes how far a version is from the track', () => {
    expect(lengthDiff(12.4)).toBe('+12s')
    expect(lengthDiff(-3)).toBe('−3s')
    expect(lengthDiff(0)).toBe('±0s')
    expect(lengthDiff(null)).toBe('')
  })

  it('calls a version within 3 s the same length', () => {
    expect(sameLength(3)).toBe(true)
    expect(sameLength(-2)).toBe(true)
    expect(sameLength(4)).toBe(false)
    expect(sameLength(null)).toBe(false)
  })

  it('offers it for library songs in formats Downtify writes', () => {
    expect(canReplace({ file: 'Artist/Song.flac' })).toBe(true)
    expect(canReplace({ file: 'Song.wav' })).toBe(false)
    expect(canReplace({ file: 'Show/Ep.mp3', isPodcast: true })).toBe(false)
    expect(canReplace(null)).toBe(false)
  })
})
