import { describe, expect, it } from 'vitest'
import { proxiedArtistPhotoUrl } from '../lib/artistPhotoProxy'

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
