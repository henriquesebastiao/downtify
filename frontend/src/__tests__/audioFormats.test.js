import { describe, expect, it } from 'vitest'
import {
  FORMATS,
  downloadsFormat,
  formatLabel,
  savedBytes,
} from '/src/lib/audioFormats'

describe('audioFormats', () => {
  it('lists the formats the server knows, lossless first', () => {
    expect(FORMATS.slice(0, 2)).toEqual(['flac', 'wav'])
    expect(FORMATS).not.toContain('mp3')
  })

  it('names formats the usual way', () => {
    expect(formatLabel('flac')).toBe('FLAC')
    expect(formatLabel('wv')).toBe('WavPack')
  })

  it('locks the Downloads format only when it is one of them', () => {
    expect(downloadsFormat('flac')).toBe('flac')
    expect(downloadsFormat('mp3')).toBe('')
    expect(downloadsFormat('original')).toBe('')
  })

  it('never reports a negative saving', () => {
    expect(savedBytes(100, 30)).toBe(70)
    expect(savedBytes(10, 30)).toBe(0)
  })
})
