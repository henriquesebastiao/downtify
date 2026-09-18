import { describe, expect, it } from 'vitest'
import {
  fileFormat,
  formatBytes,
  formatDuration,
  hueFor,
  initials,
  splitLength,
  timeAgo,
  widestClock,
} from '../lib/format.js'

describe('widestClock', () => {
  it('is the total on both sides, every digit a zero', () => {
    // A 3:30 track: the real text ("0:25 / 3:30") can never be wider.
    expect(widestClock(210)).toBe('0:00 / 0:00')
  })

  it('keeps the shape of a long track, so the hour is reserved too', () => {
    expect(widestClock(5400)).toBe('0:00:00 / 0:00:00')
    expect(widestClock(754)).toBe('00:00 / 00:00')
  })

  it('has the same length as the real clock at its longest', () => {
    for (const seconds of [59, 210, 754, 3599, 3725, 5400]) {
      const total = formatDuration(seconds)
      expect(widestClock(seconds)).toHaveLength(`${total} / ${total}`.length)
    }
  })

  it('falls back to a short clock while the duration is unknown', () => {
    expect(widestClock(0)).toBe('0:00 / 0:00')
    expect(widestClock(NaN)).toBe('0:00 / 0:00')
  })
})

describe('formatDuration', () => {
  it('formats minutes and seconds', () => {
    expect(formatDuration(184)).toBe('3:04')
    expect(formatDuration(59.9)).toBe('0:59')
  })

  it('adds hours for long mixes', () => {
    expect(formatDuration(3725)).toBe('1:02:05')
  })

  it('treats unknown or invalid lengths as zero', () => {
    expect(formatDuration(0)).toBe('0:00')
    expect(formatDuration(NaN)).toBe('0:00')
    expect(formatDuration(-3)).toBe('0:00')
  })
})

describe('splitLength', () => {
  it('rounds to whole minutes', () => {
    expect(splitLength(9060)).toEqual({ hours: 2, minutes: 31 })
    expect(splitLength(89)).toEqual({ hours: 0, minutes: 1 })
  })
})

describe('formatBytes', () => {
  it('uses binary units with one decimal below 100', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(1536)).toBe('1.5 KB')
    expect(formatBytes(312 * 1024 * 1024)).toBe('312 MB')
    expect(formatBytes(62.4 * 1024 ** 3)).toBe('62.4 GB')
  })
})

describe('timeAgo', () => {
  const now = Date.UTC(2026, 8, 16, 12, 0, 0)

  it('accepts epoch seconds', () => {
    expect(timeAgo(now / 1000 - 120, 'en', now)).toBe('2 minutes ago')
  })

  it('accepts ISO strings and says yesterday', () => {
    const iso = new Date(now - 26 * 3600 * 1000).toISOString()
    expect(timeAgo(iso, 'en', now)).toBe('yesterday')
  })

  it('follows the UI language', () => {
    expect(timeAgo(now - 3 * 3600 * 1000, 'pt-BR', now)).toBe('há 3 horas')
  })

  it('returns nothing for missing dates', () => {
    expect(timeAgo(0, 'en', now)).toBe('')
    expect(timeAgo('not a date', 'en', now)).toBe('')
  })
})

describe('helpers', () => {
  it('reads the file format from the extension', () => {
    expect(fileFormat('Album/01 - Song.flac')).toBe('FLAC')
    expect(fileFormat('no-extension')).toBe('')
  })

  it('builds initials from up to two words', () => {
    expect(initials('The Night Owls')).toBe('TN')
    expect(initials('Sable & Rye')).toBe('SR')
    expect(initials('')).toBe('')
  })

  it('derives a stable hue', () => {
    expect(hueFor('Glass Harbor')).toBe(hueFor('Glass Harbor'))
    expect(hueFor('Glass Harbor')).toBeGreaterThanOrEqual(0)
    expect(hueFor('Glass Harbor')).toBeLessThan(360)
  })
})
