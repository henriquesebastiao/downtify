import { describe, expect, it } from 'vitest'
import { activeLineIndex, parseLrc } from '../lib/lrc.js'

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
