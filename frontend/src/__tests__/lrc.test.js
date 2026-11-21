import { describe, expect, it } from 'vitest'
import {
  activeLineIndex,
  countInBeats,
  lineProgress,
  parseLrc,
} from '../lib/lrc.js'

describe('lineProgress', () => {
  const words = 'x'.repeat(40) // 40 chars: 10 seconds at most

  it('runs from the start of the line to the next one', () => {
    const lines = [
      { time: 10, text: words },
      { time: 14, text: 'next' },
    ]
    expect(lineProgress(lines, 0, 10)).toBe(0)
    expect(lineProgress(lines, 0, 12)).toBe(0.5)
    expect(lineProgress(lines, 0, 14)).toBe(1)
  })

  it('does not crawl across an untimed gap after the line', () => {
    const lines = [
      { time: 10, text: words },
      { time: 70, text: 'after the solo' },
    ]
    expect(lineProgress(lines, 0, 15)).toBe(0.5)
    expect(lineProgress(lines, 0, 20)).toBe(1)
  })

  it('gives a short line time to be sung', () => {
    const lines = [{ time: 0, text: 'Oh' }]
    expect(lineProgress(lines, 0, 1.5)).toBe(0.5)
  })

  it('stays within 0 and 1, and survives bad input', () => {
    const lines = [
      { time: 10, text: words },
      { time: 10, text: 'same time' },
    ]
    expect(lineProgress(lines, 0, 5)).toBe(1)
    expect(lineProgress(lines, 5, 5)).toBe(0)
    expect(lineProgress([{ time: 10, text: words }], 0, 5)).toBe(0)
  })
})

describe('countInBeats', () => {
  const lines = [
    { time: 8, text: 'First' },
    { time: 12, text: '' },
    { time: 30, text: 'Back in' },
    { time: 40, text: '' },
  ]

  it('holds every dot through a long intro, then counts down', () => {
    expect(countInBeats(lines, 0)).toBe(3)
    expect(countInBeats(lines, 5.5)).toBe(3)
    expect(countInBeats(lines, 6.5)).toBe(2)
    expect(countInBeats(lines, 7.5)).toBe(1)
  })

  it('counts in after an instrumental gap', () => {
    expect(countInBeats(lines, 20)).toBe(3)
    expect(countInBeats(lines, 29.5)).toBe(1)
  })

  it('shows nothing while a line is sung or when no words are left', () => {
    expect(countInBeats(lines, 9)).toBe(0)
    expect(countInBeats(lines, 45)).toBe(0)
    expect(countInBeats([], 0)).toBe(0)
  })
})

const LRC = `[ar:Kenji Aoki]
[ti:Harbor Lights]
[00:12.00]The harbor lights are blinking out
[00:15.5]One by one along the pier

[00:20.250][01:02.00]I kept the lantern burning
[00:59.00]`

describe('parseLrc', () => {
  it('reads timed lines in order and skips metadata', () => {
    const lines = parseLrc(LRC)
    expect(lines.map((l) => l.time)).toEqual([12, 15.5, 20.25, 59, 62])
    expect(lines[0].text).toBe('The harbor lights are blinking out')
  })

  it('repeats a line for each of its time tags', () => {
    const lines = parseLrc(LRC)
    expect(
      lines.filter((l) => l.text === 'I kept the lantern burning')
    ).toHaveLength(2)
  })

  it('keeps instrumental gaps as empty lines', () => {
    expect(parseLrc(LRC)[3]).toEqual({ time: 59, text: '' })
  })

  it('returns nothing for plain text', () => {
    expect(parseLrc('just words\nno timestamps')).toEqual([])
    expect(parseLrc('')).toEqual([])
  })
})

describe('activeLineIndex', () => {
  const lines = parseLrc(LRC)

  it('is -1 before the first line', () => {
    expect(activeLineIndex(lines, 3)).toBe(-1)
  })

  it('finds the line being sung', () => {
    expect(activeLineIndex(lines, 12)).toBe(0)
    expect(activeLineIndex(lines, 17)).toBe(1)
    expect(activeLineIndex(lines, 300)).toBe(4)
  })
})
