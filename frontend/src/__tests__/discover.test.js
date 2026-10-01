import { describe, expect, it } from 'vitest'
import {
  LISTEN_MAX_SECONDS,
  addPlayed,
  appendNew,
  artistRoute,
  collectionRoute,
  collectionsPayload,
  deezerArtistUrl,
  findSongsLocation,
  joinNames,
  libraryPayload,
  listenArtist,
  listenThreshold,
} from '../lib/discover'

const track = (file, extra = {}) => ({ file, ...extra })

describe('libraryPayload', () => {
  it('counts tracks and liked tracks per artist', () => {
    const artists = [
      { name: 'Air', tracks: [track('a.mp3'), track('b.mp3')] },
      { name: 'Blur', tracks: [track('c.mp3')] },
      { name: '', tracks: [track('d.mp3')] },
    ]
    expect(libraryPayload(artists, new Set(['b.mp3']))).toEqual([
      { name: 'Air', tracks: 2, liked: 1 },
      { name: 'Blur', tracks: 1, liked: 0 },
    ])
  })

  it('uses trackCount when the artist index has no track rows', () => {
    expect(
      libraryPayload(
        [{ name: 'Air', tracks: [], trackCount: 4, likedCount: 2 }],
        new Set()
      )
    ).toEqual([{ name: 'Air', tracks: 4, liked: 2 }])
  })

  it('works without likes or artists', () => {
    expect(libraryPayload(null)).toEqual([])
    expect(libraryPayload([{ name: 'Air', tracks: [track('a.mp3')] }])).toEqual(
      [{ name: 'Air', tracks: 1, liked: 0 }]
    )
  })
})

describe('listenArtist', () => {
  it('uses the name the Library groups the track under', () => {
    expect(
      listenArtist(track('a.mp3', { albumArtist: 'Various', artists: ['Air'] }))
    ).toBe('Various')
    expect(listenArtist(track('a.mp3', { artists: ['Air', 'Beck'] }))).toBe(
      'Air'
    )
  })

  it('ignores podcasts and anything that is not a library file', () => {
    expect(
      listenArtist(track('p.mp3', { isPodcast: true, artists: ['Show'] }))
    ).toBe('')
    expect(listenArtist({ artists: ['Air'] })).toBe('')
    expect(listenArtist(null)).toBe('')
  })
})

describe('listenThreshold', () => {
  it('is half the track, capped at four minutes', () => {
    expect(listenThreshold(200)).toBe(100)
    expect(listenThreshold(1200)).toBe(LISTEN_MAX_SECONDS)
  })

  it('never counts very short or unknown-length tracks', () => {
    expect(listenThreshold(20)).toBe(Infinity)
    expect(listenThreshold(0)).toBe(Infinity)
    expect(listenThreshold(undefined)).toBe(Infinity)
  })
})

describe('addPlayed', () => {
  it('adds up small forward steps', () => {
    let played = 0
    let last = 0
    for (const now of [0.25, 0.5, 1, 2, 3]) {
      played = addPlayed(played, last, now)
      last = now
    }
    expect(played).toBe(3)
  })

  it('does not count seeks', () => {
    expect(addPlayed(10, 5, 120)).toBe(10)
    expect(addPlayed(10, 120, 5)).toBe(10)
    expect(addPlayed(10, 5, 5)).toBe(10)
  })
})

describe('joinNames', () => {
  it('joins names in the page language', () => {
    expect(joinNames(['A', 'B', 'C'], 'en')).toBe('A, B, and C')
    expect(joinNames(['A', 'B'], 'pt-BR')).toBe('A e B')
    expect(joinNames(['A', '', null], 'en')).toBe('A')
  })
})

describe('deezerArtistUrl', () => {
  it('links to the artist on Deezer when there is an id', () => {
    expect(deezerArtistUrl({ deezer_id: '664' })).toBe(
      'https://www.deezer.com/artist/664'
    )
    expect(deezerArtistUrl({ name: 'X' })).toBe('')
  })
})

describe('collectionsPayload', () => {
  it('sends the artists, the albums and the downloaded playlists', () => {
    const artists = [{ name: 'Air', tracks: [track('a.mp3')] }]
    const albums = [
      { artist: 'Air', title: 'Moon Safari' },
      { artist: 'Air', title: '' },
    ]
    const playlists = [
      { name: 'Mine', batch: { spotify_playlist_id: 'pl1' } },
      { name: 'Local', batch: null },
    ]
    expect(
      collectionsPayload(artists, albums, playlists, new Set(['a.mp3']))
    ).toEqual({
      library: [{ name: 'Air', tracks: 1, liked: 1 }],
      albums: [{ artist: 'Air', title: 'Moon Safari' }],
      playlist_ids: ['pl1'],
      playlist_names: ['Mine', 'Local'],
    })
  })
})

describe('appendNew', () => {
  const deezer = (id, key) => ({ key, deezer_album_id: id, url: `dz/${id}` })

  it('adds what is new at the end, never moving what is there', () => {
    const list = [deezer('1', 'a|one'), deezer('2', 'a|two')]
    const merged = appendNew(list, [deezer('3', 'b|three')])
    expect(merged.map((item) => item.key)).toEqual([
      'a|one',
      'a|two',
      'b|three',
    ])
  })

  it('leaves out the same album, by key, Deezer id or link', () => {
    const list = [deezer('1', 'a|one')]
    const incoming = [
      { key: 'a|one', url: 'spotify/x' },
      { key: 'other', deezer_album_id: '1' },
      { key: 'again', url: 'dz/1' },
      { key: 'b|new', url: 'spotify/y' },
      { key: 'b|new', url: 'spotify/y' },
    ]
    expect(appendNew(list, incoming).map((item) => item.key)).toEqual([
      'a|one',
      'b|new',
    ])
  })

  it('keeps the same list when nothing is new', () => {
    const list = [deezer('1', 'a|one')]
    expect(appendNew(list, [deezer('1', 'a|one')])).toBe(list)
    expect(appendNew(undefined, undefined)).toEqual([])
  })
})

describe('collectionRoute', () => {
  it('opens a Deezer album in the Finder', () => {
    expect(
      collectionRoute({
        source: 'deezer',
        deezer_album_id: '302127',
        deezer_artist_id: '27',
        url: 'https://www.deezer.com/album/302127',
      })
    ).toEqual({
      name: 'FinderBrowse',
      query: { artist: '27', album: '302127' },
    })
  })

  it('opens a Spotify album or any playlist on the Link page', () => {
    const spotify = 'https://open.spotify.com/album/x'
    const playlist = 'https://www.deezer.com/playlist/3184748882'
    expect(collectionRoute({ source: 'spotify', url: spotify })).toEqual({
      name: 'Link',
      query: { url: spotify },
    })
    expect(
      collectionRoute({
        source: 'deezer',
        deezer_playlist_id: '1',
        url: playlist,
      })
    ).toEqual({ name: 'Link', query: { url: playlist } })
  })
})

describe('artistRoute', () => {
  it('opens the artist in the Finder when Deezer knows it, else searches', () => {
    expect(artistRoute({ name: 'Air', deezer_id: 1234 })).toEqual({
      name: 'FinderBrowse',
      query: { artist: '1234' },
    })
    expect(artistRoute({ name: 'Air', deezer_id: '' })).toEqual({
      name: 'Search',
      params: { query: 'Air' },
    })
  })
})

describe('findSongsLocation', () => {
  it("opens the artist's songs in the Finder by their Deezer id", () => {
    expect(
      findSongsLocation({ name: 'Charlie Brown Jr.', deezer_id: 8691 })
    ).toEqual({
      name: 'Discover',
      query: { artist: '8691', name: 'Charlie Brown Jr.' },
    })
  })

  it('searches the Finder for the name when there is no id', () => {
    expect(findSongsLocation({ name: 'Somebody', deezer_id: '' })).toEqual({
      name: 'Discover',
      query: { q: 'Somebody' },
    })
  })
})
