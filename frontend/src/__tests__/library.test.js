import { describe, expect, it } from 'vitest'
import {
  buildPlaylists,
  filterItems,
  groupAlbums,
  groupArtists,
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
    expect(playlist.covers).toHaveLength(1)
    expect(tracked).toMatchObject({ name: 'Not downloaded yet', tracks: [] })
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
