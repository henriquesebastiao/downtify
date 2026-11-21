import { describe, expect, it } from 'vitest'
import { findWatch, linkId } from '../lib/watchMatch'

const ARTIST = {
  id: 1,
  user_id: 7,
  kind: 'artist',
  name: 'Nirvana',
  spotify_id: 'UCabcdefghijklmnopqrstuv',
  url: 'https://open.spotify.com/artist/6olE6TJLqED3rqDCT0FyPh',
}
const PLAYLIST = {
  id: 2,
  user_id: 7,
  kind: 'playlist',
  name: 'Mix',
  spotify_id: '37i9dQZF1DXcBWIGoYBM5M',
  url: 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=x',
}
const DEEZER = {
  id: 3,
  user_id: 7,
  kind: 'playlist',
  name: 'Deezer mix',
  spotify_id: 'deezer:playlist:908622995',
  url: 'https://www.deezer.com/br/playlist/908622995',
}

describe('linkId', () => {
  it('reads the id out of each kind of link', () => {
    expect(
      linkId('https://open.spotify.com/intl-pt/artist/6olE6TJLqED3rqDCT0FyPh')
    ).toBe('6olE6TJLqED3rqDCT0FyPh')
    expect(linkId('https://deezer.com/playlist/908622995')).toBe('908622995')
    expect(
      linkId('https://music.youtube.com/playlist?list=PLabc_DEF-123')
    ).toBe('PLabc_DEF-123')
    expect(
      linkId('https://music.youtube.com/channel/UCabcdefghijklmnopqrstuv')
    ).toBe('UCabcdefghijklmnopqrstuv')
    expect(linkId('Nirvana')).toBe('')
  })
})

describe('findWatch', () => {
  const watches = [ARTIST, PLAYLIST, DEEZER]

  it('finds a playlist watch by its link, whatever the query string', () => {
    expect(
      findWatch(watches, {
        kind: 'playlist',
        url: 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
      })
    ).toBe(PLAYLIST)
    expect(
      findWatch(watches, {
        kind: 'playlist',
        url: 'https://www.deezer.com/playlist/908622995',
      })
    ).toBe(DEEZER)
  })

  it('finds an artist by channel, link or name (case-insensitive)', () => {
    expect(
      findWatch(watches, {
        kind: 'artist',
        url: 'https://music.youtube.com/channel/UCabcdefghijklmnopqrstuv',
      })
    ).toBe(ARTIST)
    expect(findWatch(watches, { kind: 'artist', name: ' nirvana ' })).toBe(
      ARTIST
    )
  })

  it('never matches a playlist by name, nor across kinds', () => {
    expect(findWatch(watches, { kind: 'playlist', name: 'Mix' })).toBeNull()
    expect(
      findWatch(watches, {
        kind: 'artist',
        url: 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
      })
    ).toBeNull()
  })

  it('counts only the given user’s watches', () => {
    expect(
      findWatch(watches, { kind: 'artist', name: 'Nirvana', userId: 8 })
    ).toBeNull()
    expect(
      findWatch(watches, { kind: 'artist', name: 'Nirvana', userId: 7 })
    ).toBe(ARTIST)
  })

  it('tolerates a missing list', () => {
    expect(findWatch(null, { kind: 'artist', name: 'Nirvana' })).toBeNull()
  })
})
