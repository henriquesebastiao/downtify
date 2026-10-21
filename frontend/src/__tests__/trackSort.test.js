import { describe, expect, it } from 'vitest'

import {
  TRACK_SORTS,
  sortTracks,
  trackSortByName,
  trackSortName,
} from '../lib/library.js'
import en from '../i18n/locales/en.js'

const tracks = [
  {
    file: 'b',
    title: 'Bravo',
    artist: 'Zed',
    album: 'Two',
    added: 20,
    duration: 300,
  },
  {
    file: 'a',
    title: 'alpha',
    artist: 'Yan',
    album: 'One',
    added: 30,
    duration: 100,
  },
  {
    file: 'c',
    title: 'Charlie',
    artist: 'Xi',
    album: 'Three',
    added: 10,
    duration: 200,
  },
]
const files = (list) => list.map((track) => track.file)
const order = (name) => files(sortTracks(tracks, trackSortByName(name)))

describe('sortTracks', () => {
  it('keeps the list as it came for "order"', () => {
    expect(sortTracks(tracks, { key: 'order', dir: 'asc' })).toBe(tracks)
  })

  it('sorts by added: recently added first, or oldest first', () => {
    expect(order('addedNew')).toEqual(['a', 'b', 'c'])
    expect(order('addedOld')).toEqual(['c', 'b', 'a'])
  })

  it('sorts by title, artist and album both ways', () => {
    expect(order('titleAsc')).toEqual(['a', 'b', 'c'])
    expect(order('titleDesc')).toEqual(['c', 'b', 'a'])
    expect(order('artistAsc')).toEqual(['c', 'a', 'b'])
    expect(order('artistDesc')).toEqual(['b', 'a', 'c'])
    expect(order('albumAsc')).toEqual(['a', 'c', 'b'])
    expect(order('albumDesc')).toEqual(['b', 'c', 'a'])
  })

  it('sorts by length: longest or shortest first', () => {
    expect(order('longest')).toEqual(['b', 'c', 'a'])
    expect(order('shortest')).toEqual(['a', 'c', 'b'])
  })

  it('never reorders the list it was given', () => {
    const before = files(tracks)
    order('titleDesc')
    expect(files(tracks)).toEqual(before)
  })
})

describe('sort picker names', () => {
  it('round-trips every preset', () => {
    for (const [name] of TRACK_SORTS) {
      expect(trackSortName(trackSortByName(name))).toBe(name)
    }
  })

  it('names what a column header sorted, and falls back for the rest', () => {
    expect(trackSortName({ key: 'added', dir: 'asc' })).toBe('addedNew')
    expect(trackSortName({ key: 'duration', dir: 'desc' })).toBe('shortest')
    expect(trackSortName({ key: 'added' })).toBe('addedNew')
    expect(trackSortName({ key: 'format', dir: 'asc' })).toBe('')
    expect(trackSortByName('nope')).toEqual({ key: 'added', dir: 'asc' })
  })

  it('has a label for every preset', () => {
    for (const [name] of TRACK_SORTS) {
      expect(en.library.trackSort[name], name).toBeTruthy()
    }
  })
})
