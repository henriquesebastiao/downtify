import { describe, expect, it } from 'vitest'
import { DEEZER_MEDIUM, deezerImage } from '/src/lib/deezerImage'

const COVER =
  'https://cdn-images.dzcdn.net/images/cover/5718f7c81c27e0b2417e2a4c45224f8a'
const ARTIST =
  'https://cdn-images.dzcdn.net/images/artist/638e69b9caaf9f9f3f8826febea7b543'

describe('deezerImage', () => {
  it('turns a bigger cover into the medium preset', () => {
    expect(deezerImage(`${COVER}/1000x1000-000000-80-0-0.jpg`)).toBe(
      `${COVER}/250x250-000000-80-0-0.jpg`
    )
    expect(deezerImage(`${COVER}/500x500-000000-80-0-0.jpg`)).toBe(
      `${COVER}/250x250-000000-80-0-0.jpg`
    )
  })

  it('does the same for an artist photo', () => {
    expect(deezerImage(`${ARTIST}/1000x1000-000000-80-0-0.jpg`)).toBe(
      `${ARTIST}/250x250-000000-80-0-0.jpg`
    )
  })

  it('never makes an image bigger', () => {
    const small = `${COVER}/56x56-000000-80-0-0.jpg`
    const medium = `${COVER}/250x250-000000-80-0-0.jpg`
    expect(deezerImage(small)).toBe(small)
    expect(deezerImage(medium)).toBe(medium)
  })

  it('takes another size when asked', () => {
    expect(deezerImage(`${COVER}/1000x1000-000000-80-0-0.jpg`, 500)).toBe(
      `${COVER}/500x500-000000-80-0-0.jpg`
    )
  })

  it('leaves anything that is not a sized Deezer image alone', () => {
    for (const url of [
      '',
      null,
      undefined,
      'https://i.scdn.co/image/ab67616d0000b273abc',
      'https://lh3.googleusercontent.com/abc=w1000-h1000',
      'https://api.deezer.com/album/302127/image',
      '/cover?file=Music%2Fsong.mp3',
    ]) {
      expect(deezerImage(url)).toBe(url)
    }
  })

  it('is the medium preset by default', () => {
    expect(DEEZER_MEDIUM).toBe(250)
  })
})
