import { describe, expect, it } from 'vitest'
import {
  artistPhotoSource,
  proxiedArtistPhotoUrl,
} from '../lib/artistPhotoProxy'

describe('proxiedArtistPhotoUrl', () => {
  it('points at the display-only proxy with an encoded name', () => {
    expect(proxiedArtistPhotoUrl('Panic! At The Disco')).toBe(
      '/api/artists/photo-proxy?name=Panic!%20At%20The%20Disco'
    )
  })

  it('returns nothing for a blank name', () => {
    expect(proxiedArtistPhotoUrl('  ')).toBe('')
    expect(proxiedArtistPhotoUrl(undefined)).toBe('')
  })
})

describe('artistPhotoSource', () => {
  const saved = {
    photo_url: '/downloads/Metadata/ArtistImage/Paramore.jpg',
    photo_version: 1700,
  }
  const proxy = '/api/artists/photo-proxy?name=Paramore'

  it('shows the saved photo, versioned, and never asks the proxy', () => {
    expect(artistPhotoSource('Paramore', saved, true, '/track.jpg')).toEqual({
      cover: '/downloads/Metadata/ArtistImage/Paramore.jpg?v=1700',
      fallback: '',
    })
  })

  it('makes no proxy request before the saved-photo lookup has answered', () => {
    expect(artistPhotoSource('Paramore', undefined, false)).toEqual({
      cover: '',
      fallback: '',
    })
    expect(artistPhotoSource('Paramore', undefined, false, '/t.jpg')).toEqual({
      cover: '/t.jpg',
      fallback: '',
    })
  })

  it('uses the proxy for an artist with no saved photo', () => {
    const none = { photo_url: null, photo_version: null }
    expect(artistPhotoSource('Paramore', none, true)).toEqual({
      cover: proxy,
      fallback: '',
    })
    expect(artistPhotoSource('Paramore', undefined, true)).toEqual({
      cover: proxy,
      fallback: '',
    })
  })

  it('keeps the known picture behind the proxy', () => {
    expect(artistPhotoSource('Paramore', undefined, true, '/t.jpg')).toEqual({
      cover: proxy,
      fallback: '/t.jpg',
    })
  })
})
