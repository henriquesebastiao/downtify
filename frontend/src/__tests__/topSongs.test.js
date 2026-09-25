import { describe, expect, it } from 'vitest'
import {
  playableQueue,
  playsBadge,
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

describe('playsBadge', () => {
  it('gives YouTube Music its own tone and tooltip', () => {
    expect(playsBadge({ source: 'youtube' })).toEqual({
      tone: 'ytm',
      title: 'link.playCountYoutubeMusic',
    })
  })

  it('treats everything else as Spotify, the exact count', () => {
    expect(playsBadge({ source: 'spotify' })).toEqual({
      tone: 'spotify',
      title: 'link.playCountSpotify',
    })
    expect(playsBadge({}).tone).toBe('spotify')
  })
})

describe('playableQueue', () => {
  const songs = [
    { name: 'One', artists: ['Band'] },
    { name: 'Two', artists: ['Band'] },
    { name: 'Three', artist: 'Band' },
  ]

  it('keeps the songs that are in the library, in the list order', () => {
    const tracks = { One: { file: '1.mp3' }, Three: { file: '3.mp3' } }
    const find = (artist, title) => tracks[title]
    expect(playableQueue(songs, find)).toEqual([
      { file: '1.mp3' },
      { file: '3.mp3' },
    ])
  })

  it('looks each song up by its first artist (or the plain artist field)', () => {
    const seen = []
    playableQueue(songs, (artist, title) => seen.push([artist, title]) && null)
    expect(seen).toEqual([
      ['Band', 'One'],
      ['Band', 'Two'],
      ['Band', 'Three'],
    ])
  })

  it('is empty when nothing is downloaded or there are no songs', () => {
    expect(playableQueue(songs, () => null)).toEqual([])
    expect(playableQueue(undefined, () => null)).toEqual([])
  })
})
