import { describe, expect, it } from 'vitest'
import {
  isArtistURL,
  isSpotifyArtistURL,
  isYouTubeArtistURL,
  isYouTubePlaylistURL,
  normalizeSpotifyURL,
} from '../model/url.js'

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

describe('isSpotifyArtistURL', () => {
  it('accepts a Spotify artist link, including with a locale segment', () => {
    expect(
      isSpotifyArtistURL(
        'https://open.spotify.com/artist/0p4nmQO2msCgU4IF37Wi3j'
      )
    ).toBe(true)
    expect(
      isSpotifyArtistURL(
        'https://open.spotify.com/intl-pt/artist/0p4nmQO2msCgU4IF37Wi3j'
      )
    ).toBe(true)
  })

  it('rejects other Spotify entity types and empty values', () => {
    expect(
      isSpotifyArtistURL(
        'https://open.spotify.com/track/4vfN00PlILRXy5dcXHQE9M'
      )
    ).toBe(false)
    expect(isSpotifyArtistURL('')).toBe(false)
    expect(isSpotifyArtistURL(null)).toBe(false)
  })
})

describe('isYouTubeArtistURL', () => {
  it('accepts a YouTube Music channel link', () => {
    expect(
      isYouTubeArtistURL(
        'https://music.youtube.com/channel/UCAjidy3vxRkgGVNIFqZMl_Q'
      )
    ).toBe(true)
  })

  it('accepts a YouTube Music @handle link', () => {
    expect(isYouTubeArtistURL('https://music.youtube.com/@AvrilLavigne')).toBe(
      true
    )
  })

  it('rejects playlist, album and video links', () => {
    expect(
      isYouTubeArtistURL(
        'https://music.youtube.com/playlist?list=PLx6XKQDAhfWZ4vxtvdmpkDKUnR2omdAdr'
      )
    ).toBe(false)
    expect(
      isYouTubeArtistURL('https://music.youtube.com/watch?v=5CMuZrTy6jw')
    ).toBe(false)
    expect(
      isYouTubeArtistURL('https://music.youtube.com/browse/MPREb_abc123')
    ).toBe(false)
  })

  it('rejects non-YouTube links and empty values', () => {
    expect(
      isYouTubeArtistURL(
        'https://open.spotify.com/artist/0p4nmQO2msCgU4IF37Wi3j'
      )
    ).toBe(false)
    expect(isYouTubeArtistURL('')).toBe(false)
    expect(isYouTubeArtistURL(null)).toBe(false)
  })
})

describe('isArtistURL', () => {
  it('accepts either a Spotify or a YouTube Music artist link', () => {
    expect(
      isArtistURL('https://open.spotify.com/artist/0p4nmQO2msCgU4IF37Wi3j')
    ).toBe(true)
    expect(isArtistURL('https://music.youtube.com/@AvrilLavigne')).toBe(true)
  })

  it('rejects a non-artist link', () => {
    expect(
      isArtistURL('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M')
    ).toBe(false)
  })
})
