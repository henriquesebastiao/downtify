import { describe, expect, it } from 'vitest'
import { normalizeSpotifyURL } from '../model/url.js'

describe('normalizeSpotifyURL', () => {
  it('strips the intl-xx locale segment', () => {
    expect(
      normalizeSpotifyURL(
        'https://open.spotify.com/intl-pt/album/2dZMT4gpOWtIYtvdSLT4pr?si=0lFHGvM8S-iaXdLdMCtoCA'
      )
    ).toBe(
      'https://open.spotify.com/album/2dZMT4gpOWtIYtvdSLT4pr?si=0lFHGvM8S-iaXdLdMCtoCA'
    )
  })

  it('strips regional locale segments like intl-pt-BR', () => {
    expect(
      normalizeSpotifyURL('https://open.spotify.com/intl-pt-BR/track/abc123')
    ).toBe('https://open.spotify.com/track/abc123')
  })

  it('leaves canonical URLs untouched', () => {
    const url = 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
    expect(normalizeSpotifyURL(url)).toBe(url)
  })

  it('does not touch plain search text', () => {
    expect(normalizeSpotifyURL('international music')).toBe(
      'international music'
    )
  })

  it('handles empty and null values', () => {
    expect(normalizeSpotifyURL('')).toBe('')
    expect(normalizeSpotifyURL(null)).toBe('')
  })
})
