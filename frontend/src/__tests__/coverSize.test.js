import { describe, expect, it } from 'vitest'

import { coverURL, sizedCoverURL } from '../lib/paths.js'

describe('sizedCoverURL', () => {
  it('asks the server for a scaled library cover', () => {
    expect(sizedCoverURL(coverURL('A/B.mp3'), 300)).toBe(
      '/cover?file=A%2FB.mp3&size=300'
    )
  })

  it('leaves other images and full size alone', () => {
    expect(sizedCoverURL('/playlist-cover?file=x.jpg', 300)).toBe(
      '/playlist-cover?file=x.jpg'
    )
    expect(sizedCoverURL('https://e.cdn/x.jpg', 150)).toBe(
      'https://e.cdn/x.jpg'
    )
    expect(sizedCoverURL(coverURL('a.mp3'), 0)).toBe('/cover?file=a.mp3')
    expect(sizedCoverURL('/cover?file=a.mp3&size=150', 300)).toBe(
      '/cover?file=a.mp3&size=150'
    )
    expect(sizedCoverURL('', 300)).toBe('')
  })
})
