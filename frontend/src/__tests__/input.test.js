import { describe, expect, it } from 'vitest'
import { classifyInput } from '../lib/input.js'

describe('classifyInput', () => {
  it('treats blank input as empty', () => {
    expect(classifyInput('   ')).toEqual({ type: 'empty' })
  })

  it('treats free text as a search', () => {
    expect(classifyInput(' daft punk one more time ')).toEqual({
      type: 'search',
      query: 'daft punk one more time',
    })
  })

  it.each([
    ['https://open.spotify.com/track/0DiWol3AO6WpXZgp0goxAV', 'track'],
    ['https://open.spotify.com/intl-pt/album/2dZMT4gpOWtIYtvdSLT4pr', 'album'],
    [
      'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=x',
      'playlist',
    ],
  ])('recognises Spotify %s', (url, kind) => {
    expect(classifyInput(url)).toMatchObject({
      type: 'link',
      source: 'spotify',
      kind,
    })
  })

  it('normalises localised Spotify links', () => {
    expect(
      classifyInput('https://open.spotify.com/intl-pt/album/2dZMT4gp').url
    ).toBe('https://open.spotify.com/album/2dZMT4gp')
  })

  it('rejects Spotify artists and podcasts', () => {
    expect(
      classifyInput('https://open.spotify.com/artist/4tZwfgrHOc3mvqYlEYSvVi')
    ).toMatchObject({ type: 'unsupported', kind: 'artist' })
  })

  it.each([
    ['https://music.youtube.com/watch?v=dQw4w9WgXcQ', 'track'],
    ['https://youtu.be/dQw4w9WgXcQ', 'track'],
    ['https://music.youtube.com/browse/MPREb_abc', 'album'],
    ['https://music.youtube.com/playlist?list=OLAK5uy_abc', 'album'],
    ['https://music.youtube.com/playlist?list=PLx6XKQDAhfWZ4vx', 'playlist'],
    ['https://music.youtube.com/channel/UCAjidy3vxRkgGVNIFqZMl_Q', 'artist'],
    ['https://www.youtube.com/@someartist', 'artist'],
  ])('recognises YouTube %s', (url, kind) => {
    expect(classifyInput(url)).toMatchObject({
      type: 'link',
      source: 'youtube',
      kind,
    })
  })

  it('does not search for other web links', () => {
    expect(classifyInput('https://example.com/song')).toMatchObject({
      type: 'unsupported',
    })
  })
})
