import { describe, expect, it } from 'vitest'
import {
  albumLinkFor,
  artistLinkItems,
  buildPlaylists,
  filterItems,
  groupAlbums,
  groupArtists,
  groupingArtistName,
  indexTracksBySong,
  itemTrackCount,
  isGuestOn,
  isVariousArtists,
  normalizeTrack,
  songKey,
  sortItems,
} from '../lib/library.js'

const rows = [
  {
    file: 'Glass Harbor/Kenji Aoki - Undertow.flac',
    title: 'Undertow',
    artist: 'Kenji Aoki',
    album: 'Glass Harbor',
    album_artist: 'Kenji Aoki',
    track_number: 2,
    year: '2025',
    duration: 252,
    added: 200,
    size: 30,
    has_cover: true,
  },
  {
    file: 'Glass Harbor/Kenji Aoki - Harbor Lights.flac',
    title: 'Harbor Lights',
    artist: 'Kenji Aoki, Mira Kovač',
    album: 'Glass Harbor',
    album_artist: 'Kenji Aoki',
    track_number: 1,
    duration: 221,
    added: 100,
    size: 25,
    has_cover: false,
  },
  {
    file: 'Ana Luz - Blue Hour.mp3',
    title: 'Blue Hour',
    artist: 'Ana Luz',
    album: '',
    duration: 164,
    added: 300,
    size: 8,
    has_cover: true,
    playlists: ['Late Night Drive'],
  },
]
const tracks = rows.map(normalizeTrack)

describe('normalizeTrack', () => {
  it('builds playable URLs and splits artists', () => {
    const [, harbor] = tracks
    expect(harbor.artists).toEqual(['Kenji Aoki', 'Mira Kovač'])
    expect(harbor.url).toBe(
      '/downloads/Glass%20Harbor/Kenji%20Aoki%20-%20Harbor%20Lights.flac'
    )
    expect(harbor.format).toBe('FLAC')
    expect(harbor.hasCover).toBe(false)
  })

  it('falls back to the file name for bare paths', () => {
    const track = normalizeTrack('slskd/peer/Artist - Title.mp3')
    expect(track).toMatchObject({
      title: 'Title',
      artist: 'Artist',
      albumArtist: 'Artist',
      url: '/media/slskd/peer/Artist%20-%20Title.mp3',
    })
  })

  it('plays extra-folder tracks through /media', () => {
    const track = normalizeTrack('ext/abc123def456/Artist - Title.mp3')
    expect(track.url).toBe('/media/ext/abc123def456/Artist%20-%20Title.mp3')
  })
})

describe('groupAlbums', () => {
  const albums = groupAlbums(tracks)

  it('skips tracks without an album tag', () => {
    expect(albums).toHaveLength(1)
  })

  it('orders tracks and sums the album', () => {
    const [album] = albums
    expect(album.tracks.map((t) => t.title)).toEqual([
      'Harbor Lights',
      'Undertow',
    ])
    expect(album).toMatchObject({
      title: 'Glass Harbor',
      artist: 'Kenji Aoki',
      year: '2025',
      duration: 473,
      size: 55,
      added: 200,
    })
  })

  it('uses the first track that has embedded art as the cover', () => {
    expect(albums[0].cover).toContain('Undertow')
  })
})

describe('groupArtists', () => {
  it('groups by album artist and attaches albums', () => {
    const artists = groupArtists(tracks)
    const kenji = artists.find((a) => a.name === 'Kenji Aoki')
    expect(kenji.tracks).toHaveLength(2)
    expect(kenji.albums.map((a) => a.title)).toEqual(['Glass Harbor'])
    expect(artists.find((a) => a.name === 'Ana Luz').albums).toEqual([])
  })

  it('files a duo tagged Various Artists under the artist name', () => {
    const duo = normalizeTrack({
      file: 'Acustico/Ze Neto & Cristiano - Sintonia.mp3',
      title: 'Sintonia',
      artist: 'Zé Neto & Cristiano',
      album: 'Acústico',
      album_artist: 'Various Artists',
    })
    // The duo has its own page with the track...
    expect(groupingArtistName(duo)).toBe('Zé Neto & Cristiano')
    const artists = groupArtists([duo])
    expect(artists.map((a) => a.name)).toEqual(['Zé Neto & Cristiano'])
    expect(artists[0].tracks).toHaveLength(1)
    // ...while the album keeps its tag: a "Various Artists" album stays
    // one album (Unmark as Various Artists on its page fixes a wrong tag).
    expect(duo.albumArtist).toBe('Various Artists')
    expect(groupAlbums([duo]).map((a) => a.artist)).toEqual(['Various Artists'])
    expect(artists[0].albums).toEqual([])
  })
})

describe('buildPlaylists', () => {
  const byFile = new Map(tracks.map((t) => [t.file, t]))

  it('resolves M3U files to library tracks and attaches tracking', () => {
    const [playlist, tracked] = buildPlaylists(
      [
        {
          name: 'Late Night Drive',
          files: ['Ana Luz - Blue Hour.mp3', 'gone.mp3'],
        },
      ],
      byFile,
      [
        { playlist_name: 'Late Night Drive', missing_count: 3 },
        { playlist_name: 'Not downloaded yet', missing_count: 40 },
      ]
    )
    expect(playlist.tracks.map((t) => t.title)).toEqual(['Blue Hour'])
    expect(playlist.batch.missing_count).toBe(3)
    expect(playlist.covers).toHaveLength(2)
    expect(tracked).toMatchObject({ name: 'Not downloaded yet', tracks: [] })
    expect(playlist.fileCount).toBe(2)
  })

  it('keeps the M3U added time even when tracks are not loaded', () => {
    const [playlist] = buildPlaylists(
      [
        {
          name: 'Late Night Drive',
          files: ['Ana Luz - Blue Hour.mp3'],
          added: 1700000000,
        },
      ],
      new Map()
    )
    expect(playlist.tracks).toEqual([])
    expect(playlist.fileCount).toBe(1)
    expect(playlist.added).toBe(1700000000)
    expect(playlist.covers).toEqual([
      '/cover?file=Ana%20Luz%20-%20Blue%20Hour.mp3',
    ])
  })

  it('mosaics from M3U paths when only some tracks are loaded', () => {
    const [playlist] = buildPlaylists(
      [
        {
          name: 'Rock playlist',
          files: [
            'Pearl Jam - Alive.mp3',
            'Van Halen - Devil.mp3',
            'Green Day - 21 Guns.mp3',
            'GnR - Patience.mp3',
          ],
          count: 134,
          manual: true,
        },
      ],
      byFile
    )
    expect(playlist.tracks).toEqual([])
    expect(playlist.fileCount).toBe(134)
    expect(playlist.cover).toBe('')
    expect(playlist.covers).toHaveLength(4)
    expect(playlist.covers[0]).toContain('/cover?file=')
  })

  it("points at the playlist's own artwork when it was downloaded", () => {
    const [playlist] = buildPlaylists(
      [
        {
          name: 'Late Night Drive',
          files: ['Ana Luz - Blue Hour.mp3'],
          cover: 'Late Night Drive/Late Night Drive.jpg',
        },
      ],
      byFile
    )
    expect(playlist.cover).toBe(
      '/playlist-cover?file=Late%20Night%20Drive%2FLate%20Night%20Drive.jpg'
    )
  })

  it('has no cover of its own when none was downloaded', () => {
    const [playlist] = buildPlaylists(
      [{ name: 'Late Night Drive', files: ['Ana Luz - Blue Hour.mp3'] }],
      byFile
    )
    // Falls back to the track covers, which the UI grids into a mosaic.
    expect(playlist.cover).toBe('')
    expect(playlist.covers).toHaveLength(1)
  })

  it('flags the liked songs playlist and keeps a title to show', () => {
    const [liked, regular, tracked] = buildPlaylists(
      [
        {
          name: 'Downtify Liked Songs',
          files: ['Ana Luz - Blue Hour.mp3'],
          liked: true,
        },
        { name: 'Late Night Drive', files: [] },
      ],
      byFile,
      [{ playlist_name: 'Not downloaded yet' }]
    )
    expect(liked).toMatchObject({ liked: true, title: 'Downtify Liked Songs' })
    // The title starts as the file name; the model swaps in a translation.
    expect(liked.name).toBe('Downtify Liked Songs')
    expect(regular.liked).toBe(false)
    expect(regular.manual).toBe(false)
    expect(tracked).toMatchObject({ liked: false, title: 'Not downloaded yet' })
  })

  it('flags a playlist the user created in the Library', () => {
    const [playlist] = buildPlaylists(
      [
        {
          name: 'Late Night Drive',
          files: ['Ana Luz - Blue Hour.mp3'],
          manual: true,
        },
      ],
      byFile
    )
    expect(playlist.manual).toBe(true)
    expect(playlist.cover).toBe('')
    expect(playlist.covers.length).toBeGreaterThan(0)
  })
})

describe('sortItems and filterItems', () => {
  it('sorts newest first by default', () => {
    expect(sortItems(tracks, 'added').map((t) => t.title)).toEqual([
      'Blue Hour',
      'Undertow',
      'Harbor Lights',
    ])
  })

  it('sorts by title and can reverse', () => {
    expect(sortItems(tracks, 'title', 'desc').map((t) => t.title)).toEqual([
      'Undertow',
      'Harbor Lights',
      'Blue Hour',
    ])
  })

  it('matches every word, ignoring case and accents', () => {
    const found = filterItems(tracks, 'kovac HARBOR', ['title', 'artist'])
    expect(found.map((t) => t.title)).toEqual(['Harbor Lights'])
    expect(filterItems(tracks, '', ['title'])).toBe(tracks)
  })
})

describe('songKey', () => {
  it('ignores featured artists, remasters and punctuation', () => {
    expect(
      songKey('Kenji Aoki, Mira Kovač', 'Harbor Lights (Remastered)')
    ).toBe(songKey('kenji aoki', 'Harbor  Lights'))
    expect(songKey('Ana Luz', 'Blue Hour feat. Someone')).toBe(
      songKey('Ana Luz', 'Blue Hour')
    )
    expect(songKey('Ana Luz', 'Blue Hour (with Someone)')).toBe(
      songKey('Ana Luz', 'Blue Hour')
    )
    expect(songKey('Ana Luz', 'Blue Hour - 2022 Remaster')).toBe(
      songKey('Ana Luz', 'Blue Hour')
    )
  })

  it('keeps other versions distinct', () => {
    const plain = songKey('Ana Luz', 'Blue Hour')
    expect(songKey('Ana Luz', 'Blue Hour (Cake Mix)')).not.toBe(plain)
    expect(songKey('Ana Luz', 'Blue Hour [Live]')).not.toBe(plain)
    expect(songKey('Ana Luz', 'Blue Hour (Without You)')).not.toBe(plain)
  })
})

describe('indexTracksBySong', () => {
  const a = {
    file: 'A/Ana Luz - Blue Hour.mp3',
    artist: 'Ana Luz',
    title: 'Blue Hour',
  }
  const b = {
    file: 'B/Ana Luz - Blue Hour (2).mp3',
    artist: 'Ana Luz',
    title: 'Blue Hour',
  }
  const c = {
    file: 'C/Kenji Aoki - Undertow.flac',
    artist: 'Kenji Aoki',
    title: 'Undertow',
  }

  it('finds the track behind a song by the same loose key as songKey', () => {
    const index = indexTracksBySong([a, c])
    expect(index.get(songKey('ana luz', 'Blue Hour (Remastered)'))).toBe(a)
    expect(index.get(songKey('Kenji Aoki, Someone', 'Undertow'))).toBe(c)
  })

  it('keeps the first track when two share a key', () => {
    expect(indexTracksBySong([a, b]).get(songKey('Ana Luz', 'Blue Hour'))).toBe(
      a
    )
  })

  it('has nothing for a song that is not downloaded', () => {
    expect(indexTracksBySong([a]).get(songKey('Ana Luz', 'Other Song'))).toBe(
      undefined
    )
  })

  it('copes with no tracks', () => {
    expect(indexTracksBySong([]).size).toBe(0)
    expect(indexTracksBySong(undefined).size).toBe(0)
  })
})

describe('itemTrackCount', () => {
  it('uses the M3U file count even when only some tracks are loaded', () => {
    expect(itemTrackCount({ tracks: [{}, {}], fileCount: 50 })).toBe(50)
    expect(itemTrackCount({ tracks: [], fileCount: 3 })).toBe(3)
  })

  it('prefers loaded tracks, then index counts, when there is no fileCount', () => {
    expect(itemTrackCount({ tracks: [{}, {}], trackCount: 9 })).toBe(2)
    expect(itemTrackCount({ tracks: [], trackCount: 9 })).toBe(9)
    expect(itemTrackCount({})).toBe(0)
  })
})

describe('isVariousArtists', () => {
  it('spots the album artist Downtify writes for a compilation', () => {
    expect(isVariousArtists('Various Artists')).toBe(true)
    expect(isVariousArtists(' various artists ')).toBe(true)
    expect(isVariousArtists('Various')).toBe(true)
  })

  it('leaves real artists alone', () => {
    expect(isVariousArtists('Kenji Aoki')).toBe(false)
    expect(isVariousArtists('')).toBe(false)
    expect(isVariousArtists(undefined)).toBe(false)
  })
})

describe('artists credited on a track', () => {
  // A compilation track with four artists, a regular album with a guest,
  // and one artist whose own name holds a comma.
  const credited = [
    {
      file: 'a.mp3',
      title: 'Marmalade',
      artist: 'Kenji Aoki; Mira Kovač; Ana Luz; Tom Reyes',
      artists: ['Kenji Aoki', 'Mira Kovač', 'Ana Luz', 'Tom Reyes'],
      album: 'Soundtrack',
      album_artist: 'Various Artists',
    },
    {
      file: 'b.mp3',
      title: 'Undertow',
      artist: 'Kenji Aoki; Mira Kovač',
      artists: ['Kenji Aoki', 'Mira Kovač'],
      album: 'Glass Harbor',
      album_artist: 'Kenji Aoki',
    },
    {
      file: 'c.mp3',
      title: 'September',
      artist: 'Coast, Hill & Vale',
      artists: ['Coast, Hill & Vale'],
      album: 'Best Of',
      album_artist: 'Coast, Hill & Vale',
    },
  ].map(normalizeTrack)
  const artists = groupArtists(credited)
  const byName = (name) => artists.find((a) => a.name === name)

  it('takes the artist list the server read from the ARTISTS tag', () => {
    expect(credited[2].artists).toEqual(['Coast, Hill & Vale'])
  })

  it('keeps a name with a comma whole when it is the album artist', () => {
    // No list from the server (an older backend, or a bare row).
    const track = normalizeTrack({
      file: 'd.mp3',
      artist: 'Coast, Hill & Vale',
      album_artist: 'Coast, Hill & Vale',
    })
    expect(track.artists).toEqual(['Coast, Hill & Vale'])
    expect(groupArtists([track]).map((a) => a.name)).toEqual([
      'Coast, Hill & Vale',
    ])
  })

  it('gives every credited artist a page, guests included', () => {
    expect(artists.map((a) => a.name).sort()).toEqual([
      'Ana Luz',
      'Coast, Hill & Vale',
      'Kenji Aoki',
      'Mira Kovač',
      'Tom Reyes',
    ])
    expect(byName('Mira Kovač').tracks.map((t) => t.title)).toEqual([
      'Marmalade',
      'Undertow',
    ])
    expect(byName('Kenji Aoki').tracks).toHaveLength(2)
  })

  it('never makes Various Artists a page, nor gives it albums', () => {
    expect(byName('Various Artists')).toBeUndefined()
    expect(byName('Kenji Aoki').albums.map((a) => a.title)).toEqual([
      'Glass Harbor',
    ])
    // Albums stay with their album artist only.
    expect(byName('Mira Kovač').albums).toEqual([])
  })

  it('links a track to the artist it belongs to', () => {
    expect(groupingArtistName(credited[0])).toBe('Kenji Aoki')
    expect(groupingArtistName(credited[1])).toBe('Kenji Aoki')
    expect(isGuestOn(credited[1], 'Mira Kovač')).toBe(true)
    expect(isGuestOn(credited[1], 'kenji aoki')).toBe(false)
    expect(isGuestOn(credited[0], 'Kenji Aoki')).toBe(false)
  })
})

describe('artistLinkItems', () => {
  const page = (name) => ({ name: 'Artist', query: { name } })
  const search = (name) => ({ name: 'Search', params: { query: name } })

  it('links every credited artist to their own page', () => {
    expect(artistLinkItems(['Kenji Aoki', 'Mira Kovač'])).toEqual([
      { name: 'Kenji Aoki', to: page('Kenji Aoki') },
      { name: 'Mira Kovač', to: page('Mira Kovač') },
    ])
  })

  it('links only the artists with a page for a song not in the Library', () => {
    const hasPage = (name) => name === 'Kenji Aoki'
    expect(artistLinkItems(['Kenji Aoki', 'Tom Reyes'], { hasPage })).toEqual([
      { name: 'Kenji Aoki', to: page('Kenji Aoki') },
      { name: 'Tom Reyes', to: null },
    ])
  })

  it('links the artists without a page to a search for them', () => {
    const hasPage = (name) => name === 'Kenji Aoki'
    expect(
      artistLinkItems(['Kenji Aoki', 'Tom Reyes'], {
        hasPage,
        searchMissing: true,
      })
    ).toEqual([
      { name: 'Kenji Aoki', to: page('Kenji Aoki') },
      { name: 'Tom Reyes', to: search('Tom Reyes') },
    ])
  })

  it('shows plain names, or the fallback, when nothing links', () => {
    expect(
      artistLinkItems(['Kenji Aoki'], { plain: true, searchMissing: true })
    ).toEqual([{ name: 'Kenji Aoki', to: null }])
    expect(
      artistLinkItems([], { fallback: 'Unknown artist', searchMissing: true })
    ).toEqual([{ name: 'Unknown artist', to: null }])
    expect(artistLinkItems(null)).toEqual([])
  })
})

describe('albumLinkFor', () => {
  const albums = [
    { artist: 'Kenji Aoki', title: 'Glass Harbor' },
    { artist: 'Various Artists', title: 'Soundtrack' },
    { artist: 'Ana Luz', title: 'Night' },
  ]
  const album = (artist, title) => ({
    name: 'Album',
    query: { artist, title },
  })

  it('opens the album when the Library has it', () => {
    const song = { album_name: 'glass harbor', artists: ['Kenji Aoki'] }
    expect(albumLinkFor(albums, song)).toEqual(
      album('Kenji Aoki', 'Glass Harbor')
    )
  })

  it("matches the song's album artist or any of its artists", () => {
    expect(
      albumLinkFor(albums, {
        album_name: 'Glass Harbor',
        artists: ['Mira Kovač', 'Kenji Aoki'],
      })
    ).toEqual(album('Kenji Aoki', 'Glass Harbor'))
    expect(
      albumLinkFor(albums, {
        album_name: 'Glass Harbor',
        album_artist: 'kenji aoki',
        artists: ['Tom Reyes'],
      })
    ).toEqual(album('Kenji Aoki', 'Glass Harbor'))
  })

  it("opens a compilation of that title, whoever's song it is", () => {
    expect(
      albumLinkFor(albums, { album_name: 'Soundtrack', artists: ['Tom Reyes'] })
    ).toEqual(album('Various Artists', 'Soundtrack'))
  })

  it("searches for an album the Library doesn't have", () => {
    // Same title, another artist: a namesake, not this album.
    expect(
      albumLinkFor(albums, { album_name: 'Night', artists: ['Tom Reyes'] })
    ).toEqual({ name: 'Search', params: { query: 'Tom Reyes Night' } })
  })

  it('gives no search link when searching is off', () => {
    const off = { search: false }
    expect(
      albumLinkFor(albums, { album_name: 'Night', artists: ['Tom Reyes'] }, off)
    ).toBe(null)
    // What the Library has still links.
    expect(
      albumLinkFor(
        albums,
        { album_name: 'Glass Harbor', artists: ['Kenji Aoki'] },
        off
      )
    ).toEqual(album('Kenji Aoki', 'Glass Harbor'))
  })

  it('gives no link to a song without an album', () => {
    expect(albumLinkFor(albums, { album_name: '', artists: ['A'] })).toBe(null)
    expect(albumLinkFor(albums, null)).toBe(null)
  })
})
