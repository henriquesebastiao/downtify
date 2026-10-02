import { describe, expect, it } from 'vitest'
import {
  buildPlaylists,
  filterItems,
  groupAlbums,
  groupArtists,
  indexTracksBySong,
  itemTrackCount,
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
    expect(duo.albumArtist).toBe('Zé Neto & Cristiano')
    const artists = groupArtists([duo])
    expect(artists.map((a) => a.name)).toEqual(['Zé Neto & Cristiano'])
    expect(artists[0].albums.map((a) => a.title)).toEqual(['Acústico'])
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
