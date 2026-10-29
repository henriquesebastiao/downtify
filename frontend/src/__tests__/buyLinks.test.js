import { describe, expect, it } from 'vitest'

import {
  buyTargetForSong,
  buyTargetForTrack,
  formatPrice,
  storeCountry,
  storeIcon,
} from '../lib/buyLinks.js'

describe('storeCountry', () => {
  it('takes the region of the first browser language that has one', () => {
    expect(storeCountry(['pt-BR', 'en-US'])).toBe('BR')
    expect(storeCountry(['de', 'fr_CA'])).toBe('CA')
  })

  it('falls back to the US store', () => {
    expect(storeCountry(['en'])).toBe('US')
    expect(storeCountry([])).toBe('US')
    expect(storeCountry(undefined)).toBe('US')
    expect(storeCountry(['zh-Hant'])).toBe('US')
  })
})

describe('buy targets', () => {
  it('asks for a search result by its first artist', () => {
    expect(
      buyTargetForSong({
        name: 'Roads',
        artists: ['Portishead', 'Someone'],
        album_name: 'Dummy',
      })
    ).toEqual({ artist: 'Portishead', title: 'Roads', album: 'Dummy' })
    expect(buyTargetForSong({ name: 'X', artist: 'Y' })).toEqual({
      artist: 'Y',
      title: 'X',
      album: '',
    })
  })

  it('asks for a library track the same way', () => {
    expect(
      buyTargetForTrack({
        title: 'Roads',
        artist: 'Portishead, Someone',
        artists: ['Portishead', 'Someone'],
        album: 'Dummy',
      })
    ).toEqual({ artist: 'Portishead', title: 'Roads', album: 'Dummy' })
  })
})

describe('formatPrice', () => {
  it('shows the store price in its currency', () => {
    expect(formatPrice(1.29, 'USD', 'en')).toBe('$1.29')
    expect(formatPrice(2.9, 'BRL', 'pt-BR')).toMatch(/R\$\s2,90/)
  })

  it('shows nothing without a price', () => {
    expect(formatPrice(null, 'USD', 'en')).toBe('')
    expect(formatPrice(-1, 'USD', 'en')).toBe('')
    expect(formatPrice(1, '', 'en')).toBe('')
  })
})

describe('storeIcon', () => {
  it('has an icon for every store, and a tag for others', () => {
    expect(storeIcon('itunes')).toBe('apple-music')
    expect(storeIcon('bandcamp')).toBe('bandcamp')
    expect(storeIcon('website')).toBe('globe')
    expect(storeIcon('somewhere')).toBe('tag')
  })
})
