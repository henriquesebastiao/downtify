import { describe, expect, it } from 'vitest'
import { isPersonalMix } from '../lib/spotifyMix'

describe('isPersonalMix', () => {
  it('flags the mixes, radios, Discover Weekly and Release Radar', () => {
    for (const id of [
      '37i9dQZF1EVKuMoAJjoTIw', // a mood mix ("Sad Mix")
      '37i9dQZF1E37jO8SiMT0yy', // Daily Mix
      '37i9dQZF1E4BveUiW5aK5l', // an artist radio
      '37i9dQZEVXcJZyENOWUFo7', // Discover Weekly
      '37i9dQZEVXbmvMaU5mQ7Yv', // Release Radar
    ]) {
      expect(isPersonalMix(id)).toBe(true)
      expect(
        isPersonalMix(`https://open.spotify.com/playlist/${id}?si=3a1b2d`)
      ).toBe(true)
    }
    expect(
      isPersonalMix(
        'https://open.spotify.com/intl-pt/playlist/37i9dQZF1EVKuMoAJjoTIw'
      )
    ).toBe(true)
    expect(isPersonalMix('spotify:playlist:37i9dQZF1EVKuMoAJjoTIw')).toBe(true)
  })

  it('leaves editorial and user playlists alone', () => {
    for (const link of [
      'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M', // Today's Top Hits
      'https://open.spotify.com/playlist/37i9dQZF1DZ06evO05tE88', // This Is …
      'https://open.spotify.com/playlist/1tn26MuiTyqqmwaW3zmveH',
      'https://www.deezer.com/playlist/37i9dQZF1E',
      'https://open.spotify.com/artist/37i9dQZF1EVKuMoAJjoTIw',
      '',
      null,
    ]) {
      expect(isPersonalMix(link)).toBe(false)
    }
  })
})
