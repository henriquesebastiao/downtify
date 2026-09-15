import { describe, expect, it } from 'vitest'
import { isYouTubePlaylistURL, normalizeSpotifyURL } from '../model/url.js'

describe('isYouTubePlaylistURL', () => {
  it('accepts a YouTube Music playlist link with a share param', () => {
    expect(
      isYouTubePlaylistURL(
        'https://music.youtube.com/playlist?list=PLx6XKQDAhfWZ4vxtvdmpkDKUnR2omdAdr&si=icIkqaRdB2014lcl'
      )
    ).toBe(true)
  })

  it('accepts browse and plain YouTube playlist links', () => {
    expect(
      isYouTubePlaylistURL('https://music.youtube.com/browse/VLPLabc123')
    ).toBe(true)
    expect(
      isYouTubePlaylistURL('https://www.youtube.com/playlist?list=PLabc123')
    ).toBe(true)
    expect(
      isYouTubePlaylistURL(
        'https://music.youtube.com/playlist?list=RDCLAK5uy_curated'
      )
    ).toBe(true)
  })

  it('rejects albums, radio mixes and songs inside a playlist', () => {
    expect(
      isYouTubePlaylistURL(
        'https://music.youtube.com/playlist?list=OLAK5uy_album'
      )
    ).toBe(false)
    expect(
      isYouTubePlaylistURL('https://music.youtube.com/playlist?list=RDAMVMabc')
    ).toBe(false)
    expect(
      isYouTubePlaylistURL(
        'https://music.youtube.com/watch?v=5CMuZrTy6jw&list=PLabc123'
      )
    ).toBe(false)
  })

  it('rejects non-YouTube links and empty values', () => {
    expect(
      isYouTubePlaylistURL('https://open.spotify.com/playlist/37i9dQZF1')
    ).toBe(false)
    expect(isYouTubePlaylistURL('')).toBe(false)
    expect(isYouTubePlaylistURL(null)).toBe(false)
  })
})

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
