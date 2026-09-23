import { describe, expect, it } from 'vitest'
import {
  sanitizePlaylistName,
  topSongsBatchOptions,
  topSongsPlaylistName,
} from '../lib/topSongs.js'

const artist = { name: 'Test Artist', cover_url: 'https://example.test/a.jpg' }

describe('topSongsBatchOptions', () => {
  it('makes a named playlist with a cover when "Create playlist" is on', () => {
    expect(topSongsBatchOptions(artist, true)).toEqual({
      playlistName: 'Top Songs of Test Artist',
      coverUrl: 'https://example.test/a.jpg',
      m3u: true,
    })
  })

  it('sends plain downloads when it is off: no folder, M3U or cover', () => {
    expect(topSongsBatchOptions(artist, false)).toEqual({
      playlistName: '',
      coverUrl: '',
      m3u: false,
    })
  })

  it('copes with an artist that has no photo', () => {
    expect(
      topSongsBatchOptions({ name: 'No Photo', cover_url: '' }, true).coverUrl
    ).toBe('')
  })
})

describe('sanitizePlaylistName', () => {
  // Expected values come from the backend's m3u.sanitize_playlist_name.
  it.each([
    ['Top Songs of AC/DC', 'Top Songs of ACDC'],
    ['Top Songs of  Guns   N’ Roses ', 'Top Songs of Guns N’ Roses'],
    ['Top Songs of What?', 'Top Songs of What'],
    ['Top Songs of Mr. ', 'Top Songs of Mr'],
    ['Top Songs of P!nk', 'Top Songs of P!nk'],
    ['Top Songs of "Weird Al" Yankovic', 'Top Songs of Weird Al Yankovic'],
    ['Top Songs of Tab	here', 'Top Songs of Tabhere'],
    ['...', 'playlist'],
    ['', 'playlist'],
  ])('turns %j into %j', (input, expected) => {
    expect(sanitizePlaylistName(input)).toBe(expected)
  })
})

describe('topSongsPlaylistName', () => {
  it('is the name the library lists the playlist under', () => {
    expect(topSongsPlaylistName({ name: 'AC/DC' })).toBe('Top Songs of ACDC')
    expect(topSongsPlaylistName({ name: 'Avril Lavigne' })).toBe(
      'Top Songs of Avril Lavigne'
    )
  })
})
