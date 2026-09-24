import { describe, expect, it } from 'vitest'
import {
  artCandidates,
  artImageKey,
  isCurrentArt,
  isImageUrlQuery,
  sourceIcon,
  sourceLabel,
  versionedArtUrl,
} from '../lib/artistArt.js'

describe('isImageUrlQuery', () => {
  it('recognises http(s) links', () => {
    expect(isImageUrlQuery('https://example.com/photo.jpg')).toBe(true)
    expect(isImageUrlQuery('http://example.com/photo.jpg')).toBe(true)
  })

  it('treats a plain artist name as not a link', () => {
    expect(isImageUrlQuery('Avril Lavigne')).toBe(false)
  })

  it('ignores surrounding whitespace', () => {
    expect(isImageUrlQuery('  https://example.com/photo.jpg  ')).toBe(true)
  })

  it('treats blank input as not a link', () => {
    expect(isImageUrlQuery('')).toBe(false)
    expect(isImageUrlQuery('   ')).toBe(false)
  })
})

describe('sourceLabel', () => {
  it('maps known sources to their display name', () => {
    expect(sourceLabel('spotify')).toBe('Spotify')
    expect(sourceLabel('youtube')).toBe('YouTube Music')
    expect(sourceLabel('deezer')).toBe('Deezer')
  })

  it('uses the given label for a pasted link', () => {
    expect(sourceLabel('link', 'Link')).toBe('Link')
  })

  it('falls back to the raw source for anything unknown', () => {
    expect(sourceLabel('mystery')).toBe('mystery')
  })
})

describe('sourceIcon', () => {
  it('maps each source to its own icon', () => {
    expect(sourceIcon('spotify')).toBe('spotify')
    expect(sourceIcon('youtube')).toBe('youtube')
    expect(sourceIcon('deezer')).toBe('deezer')
    expect(sourceIcon('link')).toBe('link')
    expect(sourceIcon('upload')).toBe('upload')
  })

  it('falls back to the link icon for anything unknown', () => {
    expect(sourceIcon('mystery')).toBe('link')
  })
})

describe('artCandidates', () => {
  it('puts the Spotify candidate first when present', () => {
    const spotify = { source: 'spotify', name: 'A', image_url: 'a.jpg' }
    const results = [{ source: 'deezer', name: 'B', image_url: 'b.jpg' }]
    expect(artCandidates(spotify, results)).toEqual([spotify, ...results])
  })

  it('returns just the search results when there is no Spotify candidate', () => {
    const results = [{ source: 'deezer', name: 'B', image_url: 'b.jpg' }]
    expect(artCandidates(null, results)).toEqual(results)
  })

  it('survives a missing or malformed results list', () => {
    expect(artCandidates(null, undefined)).toEqual([])
    expect(artCandidates(null, 'not-an-array')).toEqual([])
  })
})

describe('versionedArtUrl', () => {
  const url = '/downloads/Metadata/ArtistImage/Avril Lavigne.jpg'

  it('puts the version in the URL', () => {
    expect(versionedArtUrl(url, 1758700000123)).toBe(`${url}?v=1758700000123`)
  })

  it('gives a replaced image a different URL than before', () => {
    expect(versionedArtUrl(url, 2)).not.toBe(versionedArtUrl(url, 1))
  })

  it('keeps an untouched image on one URL, so the browser can cache it', () => {
    expect(versionedArtUrl(url, 7)).toBe(versionedArtUrl(url, 7))
  })

  it('is empty when there is no image', () => {
    expect(versionedArtUrl(null, 5)).toBe('')
    expect(versionedArtUrl(undefined, 5)).toBe('')
    expect(versionedArtUrl('', 5)).toBe('')
  })

  it('leaves the URL alone when no version came with it', () => {
    expect(versionedArtUrl(url, null)).toBe(url)
    expect(versionedArtUrl(url, undefined)).toBe(url)
  })

  it('appends to a URL that already has a query', () => {
    expect(versionedArtUrl(`${url}?x=1`, 9)).toBe(`${url}?x=1&v=9`)
  })
})

describe('artImageKey', () => {
  it('reduces a Spotify URL to its path, whichever CDN host served it', () => {
    const path = '/image/ab6761610000e5eb527d95dabbe8b8b527e8136f'
    expect(artImageKey(`https://image-cdn-ak.spotifycdn.com${path}`)).toBe(path)
    expect(artImageKey(`https://image-cdn-fa.spotifycdn.com${path}`)).toBe(path)
    expect(artImageKey(path)).toBe(path)
  })

  it('drops the query string', () => {
    expect(artImageKey('https://cdn.test/image/abc?token=1#x')).toBe(
      '/image/abc'
    )
  })

  it('drops the size a YouTube Music image was asked for', () => {
    const id = '/uE72emEZFH3TVtCZoIFYKmnf7vsb42RYQxb4X'
    expect(
      artImageKey(`https://lh3.googleusercontent.com${id}=w600-h600-l90-rj`)
    ).toBe(id)
    expect(artImageKey(`${id}=w1200-h1200-l90-rj`)).toBe(id)
  })

  it("drops the size in a Deezer image's file name, keeping the hash", () => {
    const hash = '/images/artist/4886905210739af3438990897bad3a98'
    expect(
      artImageKey(
        `https://cdn-images.dzcdn.net${hash}/1000x1000-000000-80-0-0.jpg`
      )
    ).toBe(hash)
    expect(artImageKey(`${hash}/500x500-000000-80-0-0.jpg`)).toBe(hash)
  })

  it('tells two different images apart', () => {
    expect(artImageKey('/image/aaa')).not.toBe(artImageKey('/image/bbb'))
  })

  it('is empty for what is not a URL or a path', () => {
    for (const value of [
      '',
      null,
      undefined,
      'spotify',
      'upload',
      'https://',
    ]) {
      expect(artImageKey(value)).toBe('')
    }
  })
})

describe('isCurrentArt', () => {
  const candidate = {
    source: 'spotify',
    image_url: 'https://image-cdn-ak.spotifycdn.com/image/ab67photo',
  }

  it('marks the candidate whose image is the one saved', () => {
    expect(isCurrentArt(candidate, '/image/ab67photo')).toBe(true)
  })

  it('still matches when the CDN host differs from the recorded one', () => {
    const other = {
      image_url: 'https://image-cdn-fa.spotifycdn.com/image/ab67photo',
    }
    expect(isCurrentArt(other, '/image/ab67photo')).toBe(true)
  })

  it('does not mark a different image', () => {
    expect(isCurrentArt(candidate, '/image/ab67other')).toBe(false)
  })

  it('marks nothing for an upload, an old source-only value or no value', () => {
    for (const current of ['upload', 'spotify', '', null, undefined]) {
      expect(isCurrentArt(candidate, current)).toBe(false)
    }
  })

  it('copes with a candidate that has no image', () => {
    expect(isCurrentArt({}, '/image/ab67photo')).toBe(false)
    expect(isCurrentArt(undefined, '/image/ab67photo')).toBe(false)
  })
})
