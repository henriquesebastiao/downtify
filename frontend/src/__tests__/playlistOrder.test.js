import { describe, expect, it } from 'vitest'

import {
  buildPlaylists,
  moveItem,
  sortItems,
  trackRowKey,
  withRepeats,
} from '../lib/library.js'

const track = (file, title = file) => ({ file, title, duration: 60 })

describe('songs a Library playlist repeats', () => {
  it('gives the second copy on its own object and occurrence', () => {
    const a = track('a.mp3')
    const b = track('b.mp3')
    const rows = withRepeats([a, b, a, a])
    expect(rows[0]).toBe(a)
    expect(rows[1]).toBe(b)
    expect(rows[2]).not.toBe(a)
    expect(rows.map((row) => row.occurrence || 0)).toEqual([0, 0, 1, 2])
    expect(rows[3].title).toBe('a.mp3')
  })

  it('keys each copy apart, a song listed once by its file', () => {
    const rows = withRepeats([track('a.mp3'), track('a.mp3')])
    const keys = rows.map(trackRowKey)
    expect(keys[0]).toBe('a.mp3')
    expect(new Set(keys).size).toBe(2)
  })

  it('keeps the copies apart once sorted the other way round', () => {
    const rows = withRepeats([track('a.mp3', 'Zed'), track('b.mp3', 'Abe')])
    const repeated = withRepeats([...rows, rows[0]])
    const sorted = sortItems(repeated, 'title', 'desc')
    expect(sorted.map((row) => row.occurrence || 0)).toEqual([1, 0, 0])
  })

  it('builds a playlist with every copy, counted in its length', () => {
    const a = track('a.mp3')
    const [playlist] = buildPlaylists(
      [
        {
          name: 'Loop',
          files: ['a.mp3', 'b.mp3', 'a.mp3'],
          count: 3,
          manual: true,
        },
      ],
      new Map([
        ['a.mp3', a],
        ['b.mp3', track('b.mp3')],
      ])
    )
    expect(playlist.tracks.map((row) => row.file)).toEqual([
      'a.mp3',
      'b.mp3',
      'a.mp3',
    ])
    expect(playlist.tracks[2].occurrence).toBe(1)
    expect(playlist.duration).toBe(180)
    expect(playlist.covers).toHaveLength(2)
  })
})

describe('moveItem', () => {
  it('moves up, down and to either end without changing the list', () => {
    const list = ['a', 'b', 'c', 'd']
    expect(moveItem(list, 2, 1)).toEqual(['a', 'c', 'b', 'd'])
    expect(moveItem(list, 0, 3)).toEqual(['b', 'c', 'd', 'a'])
    expect(moveItem(list, 3, 0)).toEqual(['d', 'a', 'b', 'c'])
    expect(list).toEqual(['a', 'b', 'c', 'd'])
  })
})
