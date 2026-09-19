import { describe, expect, it } from 'vitest'
import {
  countWatches,
  filterWatches,
  sortWatches,
  watchKind,
  watchKindOfUrl,
} from '../lib/watches.js'

const watches = [
  {
    id: 1,
    kind: 'playlist',
    name: 'Today’s Top Hits',
    url: 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
    enabled: true,
    created_at: '2026-01-02T00:00:00',
    last_checked: '2026-03-01T00:00:00',
    interval_minutes: 60,
    last_track_count: 50,
  },
  {
    id: 2,
    kind: 'artist',
    name: 'Anitta',
    url: 'https://music.youtube.com/channel/UCabc',
    enabled: false,
    created_at: '2026-01-03T00:00:00',
    last_checked: null,
    interval_minutes: 1440,
    last_track_count: 80,
  },
  {
    id: 3,
    // Saved before artist watches existed.
    name: 'Músicas Brasileiras',
    url: 'https://music.youtube.com/playlist?list=PLxyz',
    enabled: false,
    created_at: '2026-01-01T00:00:00',
    last_checked: '2026-02-01T00:00:00',
    interval_minutes: 360,
    last_track_count: 12,
  },
]

describe('watchKind', () => {
  it('treats rows without a kind as playlists', () => {
    expect(watches.map(watchKind)).toEqual(['playlist', 'artist', 'playlist'])
  })
})

describe('watchKindOfUrl', () => {
  it.each([
    ['https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M', 'playlist'],
    ['https://open.spotify.com/intl-pt/playlist/37i9dQZF1DX?si=1', 'playlist'],
    ['https://music.youtube.com/playlist?list=PLxyz', 'playlist'],
    ['https://www.youtube.com/playlist?list=PLxyz', 'playlist'],
    ['https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg', 'artist'],
    ['https://music.youtube.com/channel/UCabcdef', 'artist'],
    ['https://music.youtube.com/@anitta', 'artist'],
    ['https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy', null],
    ['https://music.youtube.com/playlist?list=OLAK5uy_album', null],
    ['https://example.com/x', null],
    ['just words', null],
    ['', null],
  ])('%s → %s', (url, kind) => {
    expect(watchKindOfUrl(url)).toBe(kind)
  })
})

describe('countWatches', () => {
  it('counts per tab', () => {
    expect(countWatches(watches)).toEqual({ playlist: 2, artist: 1 })
    expect(countWatches([])).toEqual({ playlist: 0, artist: 0 })
  })
})

describe('filterWatches', () => {
  const ids = (list) => list.map((item) => item.id)

  it('keeps one kind', () => {
    expect(ids(filterWatches(watches, { kind: 'playlist' }))).toEqual([1, 3])
    expect(ids(filterWatches(watches, { kind: 'artist' }))).toEqual([2])
  })

  it('keeps paused ones only', () => {
    expect(
      ids(filterWatches(watches, { kind: 'playlist', paused: true }))
    ).toEqual([3])
  })

  it('matches name or link, ignoring case and accents', () => {
    const find = (query) =>
      ids(filterWatches(watches, { kind: 'playlist', query }))
    expect(find('musicas')).toEqual([3])
    expect(find('TOP hits')).toEqual([1])
    expect(find('37i9dQZF1DXcBWIGoYBM5M')).toEqual([1])
    expect(find('youtube')).toEqual([3])
    expect(find('top youtube')).toEqual([])
    expect(find('   ')).toEqual([1, 3])
  })
})

describe('sortWatches', () => {
  const ids = (list) => list.map((item) => item.id)

  it('sorts by date added', () => {
    expect(ids(sortWatches(watches, 'created_at', 'desc'))).toEqual([2, 1, 3])
    expect(ids(sortWatches(watches, 'created_at', 'asc'))).toEqual([3, 1, 2])
  })

  it('puts never-checked watches last when newest first', () => {
    expect(ids(sortWatches(watches, 'last_checked', 'desc'))).toEqual([1, 3, 2])
  })

  it('sorts by name and numbers', () => {
    expect(ids(sortWatches(watches, 'name', 'asc'))).toEqual([2, 3, 1])
    expect(ids(sortWatches(watches, 'last_track_count', 'desc'))).toEqual([
      2, 1, 3,
    ])
  })

  it('does not change the input', () => {
    const copy = [...watches]
    sortWatches(watches, 'name', 'asc')
    expect(watches).toEqual(copy)
  })
})
