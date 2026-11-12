import { describe, expect, it } from 'vitest'
import { localCatalogRoute } from '../lib/library'
import { collectionRoute, artistRoute } from '../lib/discover'

describe('local results use the existing library screens', () => {
  it('opens an album and artist without resolving an external link', () => {
    expect(
      collectionRoute({
        source: 'library',
        kind: 'album',
        name: 'Debut',
        artist: 'Björk',
      })
    ).toEqual({ name: 'Album', query: { artist: 'Björk', title: 'Debut' } })
    expect(artistRoute({ source: 'library', name: 'Björk' })).toEqual({
      name: 'Artist',
      query: { name: 'Björk' },
    })
  })

  it('keeps a playlist real identity independently of its display name', () => {
    expect(
      localCatalogRoute({
        source: 'library',
        kind: 'playlist',
        name: 'My mix',
        playlist_name: 'real.m3u',
      })
    ).toEqual({ name: 'Playlist', query: { name: 'real.m3u' } })
    expect(localCatalogRoute({ source: 'deezer', name: 'Debut' })).toBeNull()
  })
})
