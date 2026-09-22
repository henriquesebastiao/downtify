import { describe, expect, it } from 'vitest'
import {
  artCandidates,
  isImageUrlQuery,
  sourceBadgeColor,
  sourceIcon,
  sourceLabel,
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

describe('sourceBadgeColor', () => {
  it('gives each brand source its own color token', () => {
    expect(sourceBadgeColor('spotify')).toBe('var(--color-spotify)')
    expect(sourceBadgeColor('youtube')).toBe('var(--color-src-ytm)')
    expect(sourceBadgeColor('deezer')).toBe('var(--color-deezer)')
  })

  it('gives link and upload the same neutral accent color', () => {
    expect(sourceBadgeColor('link')).toBe('var(--color-accent)')
    expect(sourceBadgeColor('upload')).toBe('var(--color-accent)')
  })

  it('falls back to a muted color for anything unknown', () => {
    expect(sourceBadgeColor('mystery')).toBe('var(--color-muted)')
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
