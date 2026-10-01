import { describe, expect, it } from 'vitest'
import {
  RECENT_LIMIT,
  addRecent,
  browseLocation,
  chunk,
  clampColumnWidths,
  matchesReleaseType,
  missingTrackCounts,
  releaseTypes,
} from '/src/lib/finder'

describe('browseLocation', () => {
  it('opens an artist on its own', () => {
    expect(browseLocation('artist', { artist_id: '27' })).toEqual({
      name: 'FinderBrowse',
      query: { artist: '27' },
    })
  })

  it('opens an album on its artist, with the album selected', () => {
    expect(
      browseLocation('album', { artist_id: 27, album_id: 302127 })
    ).toEqual({
      name: 'FinderBrowse',
      query: { artist: '27', album: '302127' },
    })
  })

  it('opens a song on its album, pointing at the song', () => {
    const song = {
      song_id: 'deezer-3135553',
      deezer_artist_id: '27',
      deezer_album_id: '302127',
    }
    expect(browseLocation('song', song)).toEqual({
      name: 'FinderBrowse',
      query: { artist: '27', album: '302127', track: 'deezer-3135553' },
    })
  })

  it('opens a song without an album id on just its artist', () => {
    const song = { song_id: 'deezer-1', deezer_artist_id: '27' }
    expect(browseLocation('song', song).query).toEqual({ artist: '27' })
  })

  it('gives nothing when the id it needs is missing', () => {
    expect(browseLocation('artist', {})).toBeNull()
    expect(browseLocation('album', { album_id: '1' })).toBeNull()
    expect(browseLocation('song', { song_id: 'deezer-1' })).toBeNull()
    expect(browseLocation('song', null)).toBeNull()
  })
})

describe('missingTrackCounts', () => {
  const albums = [
    { album_id: '1', track_count: 12 },
    { album_id: '2', track_count: null },
    { album_id: '3' },
    { album_id: '4', track_count: 0 },
    { album_id: '5', track_count: null },
    { album_id: '2', track_count: null },
  ]

  it('lists the unknown ones once, in order', () => {
    expect(missingTrackCounts(albums)).toEqual(['2', '3', '5'])
  })

  it('skips counts already known or being fetched', () => {
    expect(missingTrackCounts(albums, { 3: 10 }, new Set(['5']))).toEqual(['2'])
  })

  it('keeps a zero count as known', () => {
    expect(missingTrackCounts([{ album_id: '4', track_count: 0 }])).toEqual([])
  })
})

describe('clampColumnWidths', () => {
  const min = [200, 220, 360]

  it('keeps widths that fit as they are', () => {
    expect(clampColumnWidths([300, 340], 1200, min)).toEqual([300, 340])
  })

  it('never goes under a column minimum', () => {
    expect(clampColumnWidths([50, 10], 1200, min)).toEqual([200, 220])
  })

  it('leaves the tracks column its minimum, squeezing discography first', () => {
    // 1200 - 360 for tracks = 840 for the other two.
    expect(clampColumnWidths([500, 500], 1200, min)).toEqual([500, 340])
    // The artist column can't take the discography's minimum either.
    expect(clampColumnWidths([900, 300], 1200, min)).toEqual([620, 220])
  })

  it('rounds to whole pixels', () => {
    expect(clampColumnWidths([300.4, 340.6], 1200, min)).toEqual([300, 341])
  })
})

describe('chunk', () => {
  it('splits into batches, the last one shorter', () => {
    expect(chunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]])
    expect(chunk([], 3)).toEqual([])
  })
})

describe('releaseTypes / matchesReleaseType', () => {
  const albums = [
    { release_type: 'Single' },
    { release_type: 'Album' },
    { release_type: 'Single' },
    { release_type: 'EP' },
    {},
  ]

  it('counts each type in first-seen order, untyped as albums', () => {
    expect(releaseTypes(albums)).toEqual([
      { id: 'single', count: 2 },
      { id: 'album', count: 2 },
      { id: 'ep', count: 1 },
    ])
  })

  it('filters by type, "all" keeping everything', () => {
    expect(albums.filter((a) => matchesReleaseType(a, 'single'))).toHaveLength(
      2
    )
    expect(albums.filter((a) => matchesReleaseType(a, 'album'))).toHaveLength(2)
    expect(albums.filter((a) => matchesReleaseType(a, 'all'))).toHaveLength(5)
  })
})

describe('addRecent', () => {
  it('puts the new search first, once', () => {
    expect(addRecent(['b', 'a', 'c'], 'a')).toEqual(['a', 'b', 'c'])
    expect(addRecent([], ' daft punk ')).toEqual(['daft punk'])
  })

  it('keeps at most the limit, dropping the oldest', () => {
    const full = Array.from({ length: RECENT_LIMIT }, (_, i) => `t${i}`)
    const next = addRecent(full, 'new')
    expect(next).toHaveLength(RECENT_LIMIT)
    expect(next[0]).toBe('new')
    expect(next).not.toContain(`t${RECENT_LIMIT - 1}`)
  })

  it('changes nothing for a blank search', () => {
    const list = ['a']
    expect(addRecent(list, '   ')).toBe(list)
    expect(addRecent(undefined, '')).toEqual([])
  })
})
