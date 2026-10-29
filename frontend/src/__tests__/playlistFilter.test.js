import { describe, expect, it } from 'vitest'

import {
  filterPlaylistSongs,
  filterPlaylistTracks,
  isSongView,
  providerCounts,
  providerOf,
} from '../lib/playlistFilter.js'

const track = (file, title, artist, album = '') => ({
  file,
  title,
  artist,
  album,
})

// A playlist far longer than what the virtualized list renders at once.
const TRACKS = [
  track('pl/a.mp3', 'Roads', 'Portishead', 'Dummy'),
  track('pl/b.flac', 'Teardrop', 'Massive Attack', 'Mezzanine'),
  track('slskd/c.flac', 'Glory Box', 'Portishead', 'Dummy'),
  track('ext/x1/d.mp3', 'Café', 'Zé Ninguém'),
  ...Array.from({ length: 2000 }, (_, i) =>
    track(`pl/filler-${i}.mp3`, `Filler ${i}`, 'Someone')
  ),
]
const PROVIDERS = {
  'pl/a.mp3': 'youtube-music',
  'pl/b.flac': 'slskd',
  'slskd/c.flac': 'slskd',
  'ext/x1/d.mp3': 'folder',
}

describe('filterPlaylistTracks', () => {
  it('searches every song, not just the rendered ones', () => {
    const found = filterPlaylistTracks(TRACKS, { query: 'filler 1999' })
    expect(found.map((t) => t.file)).toEqual(['pl/filler-1999.mp3'])
  })

  it('matches every word anywhere, ignoring case and accents', () => {
    expect(
      filterPlaylistTracks(TRACKS, { query: 'PORTISHEAD dummy' }).map(
        (t) => t.title
      )
    ).toEqual(['Roads', 'Glory Box'])
    expect(
      filterPlaylistTracks(TRACKS, { query: 'cafe ze' }).map((t) => t.title)
    ).toEqual(['Café'])
    expect(filterPlaylistTracks(TRACKS, { query: 'b.flac' })).toHaveLength(1)
  })

  it('keeps every song without a query or a filter', () => {
    expect(filterPlaylistTracks(TRACKS)).toBe(TRACKS)
  })

  it('narrows to one provider, unknown included', () => {
    const slskd = filterPlaylistTracks(TRACKS, {
      view: 'provider:slskd',
      providers: PROVIDERS,
    })
    expect(slskd.map((t) => t.title)).toEqual(['Teardrop', 'Glory Box'])
    const unknown = filterPlaylistTracks(TRACKS, {
      view: 'provider:',
      providers: PROVIDERS,
      query: 'filler 7',
    })
    expect(unknown.map((t) => t.file)).toContain('pl/filler-7.mp3')
    expect(unknown.every((t) => !PROVIDERS[t.file])).toBe(true)
  })

  it('narrows to the songs Navidrome has not matched', () => {
    const found = filterPlaylistTracks(TRACKS, {
      view: 'navidrome',
      unmatched: ['pl/b.flac', 'pl/filler-3.mp3'],
      query: 'teardrop',
    })
    expect(found.map((t) => t.file)).toEqual(['pl/b.flac'])
  })
})

describe('providerCounts', () => {
  it('counts each provider, in a fixed order with unknown last', () => {
    expect(providerCounts(TRACKS, PROVIDERS)).toEqual([
      { id: 'youtube-music', count: 1 },
      { id: 'slskd', count: 2 },
      { id: 'folder', count: 1 },
      { id: '', count: 2000 },
    ])
    expect(providerOf(TRACKS[0], PROVIDERS)).toBe('youtube-music')
  })

  it('offers nothing when every song has the same provider', () => {
    expect(providerCounts(TRACKS.slice(4), PROVIDERS)).toEqual([])
    expect(providerCounts([], {})).toEqual([])
  })
})

describe('missing songs', () => {
  it('are searched by title, artists and album', () => {
    const songs = [
      { song_id: '1', name: 'Roads', artists: ['Portishead'] },
      {
        song_id: '2',
        name: 'Unfinished Sympathy',
        artists: ['Massive Attack'],
        album_name: 'Blue Lines',
      },
    ]
    expect(filterPlaylistSongs(songs, 'massive').map((s) => s.song_id)).toEqual(
      ['2']
    )
    expect(filterPlaylistSongs(songs, 'blue lines')).toHaveLength(1)
    expect(filterPlaylistSongs(songs, '')).toBe(songs)
    expect(isSongView('missing')).toBe(true)
    expect(isSongView('failed')).toBe(true)
    expect(isSongView('all')).toBe(false)
  })
})
