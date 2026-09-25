import { describe, expect, it } from 'vitest'
import {
  artistPlatformLinks,
  artistSocialLinks,
  linkHost,
  safeLinkUrl,
} from '../lib/artistLinks'

describe('safeLinkUrl', () => {
  it('keeps an http(s) address as it is', () => {
    expect(safeLinkUrl('https://x.com/paramore')).toBe('https://x.com/paramore')
    expect(safeLinkUrl('http://paramore.net')).toBe('http://paramore.net')
    expect(safeLinkUrl('  HTTPS://Paramore.net  ')).toBe('HTTPS://Paramore.net')
  })

  it('makes a bare address https', () => {
    expect(safeLinkUrl('twitter.com/paramore')).toBe(
      'https://twitter.com/paramore'
    )
  })

  it('drops anything with another scheme, and nothing at all', () => {
    expect(safeLinkUrl('javascript:alert(1)')).toBe('')
    expect(safeLinkUrl('JavaScript:alert(1)')).toBe('')
    expect(safeLinkUrl('data:text/html,<script>')).toBe('')
    expect(safeLinkUrl('mailto:a@b.c')).toBe('')
    expect(safeLinkUrl('')).toBe('')
    expect(safeLinkUrl('   ')).toBe('')
    expect(safeLinkUrl(null)).toBe('')
    expect(safeLinkUrl(undefined)).toBe('')
  })
})

describe('linkHost', () => {
  it('is the site, without www', () => {
    expect(linkHost('https://open.spotify.com/artist/abc')).toBe(
      'open.spotify.com'
    )
    expect(linkHost('https://www.deezer.com/artist/1')).toBe('deezer.com')
  })

  it('falls back to the text when it is not an address', () => {
    expect(linkHost('not a url')).toBe('not a url')
    expect(linkHost('')).toBe('')
  })
})

describe('artistSocialLinks', () => {
  it('lists the filled-in fields in a fixed order', () => {
    const links = artistSocialLinks({
      website: 'https://p.example',
      twitter: 'https://x.com/p',
      facebook: '',
      instagram: 'instagram.com/p',
      youtube: '  ',
    })
    expect(links.map((l) => l.key)).toEqual(['twitter', 'instagram', 'website'])
    expect(links[1].url).toBe('https://instagram.com/p')
    expect(links[0]).toEqual({
      key: 'twitter',
      url: 'https://x.com/p',
      icon: 'twitter',
      label: 'Twitter/X',
    })
  })

  it('never lets a non-web address through', () => {
    expect(
      artistSocialLinks({ website: 'javascript:alert(1)', twitter: 'x.com/p' })
    ).toEqual([
      {
        key: 'twitter',
        url: 'https://x.com/p',
        icon: 'twitter',
        label: 'Twitter/X',
      },
    ])
  })

  it('is empty for no profile', () => {
    expect(artistSocialLinks({})).toEqual([])
    expect(artistSocialLinks(null)).toEqual([])
  })
})

describe('artistPlatformLinks', () => {
  it('builds each known platform from its saved id', () => {
    const links = artistPlatformLinks({
      spotify: '74XFHRwlV6OrjEM0A2NCMF',
      deezer: ' 1234 ',
      applemusic: 'paramore/75950796',
      youtubemusic: '',
      unknown: 'skipped',
    })
    expect(links.map((l) => [l.key, l.url])).toEqual([
      ['spotify', 'https://open.spotify.com/artist/74XFHRwlV6OrjEM0A2NCMF'],
      ['deezer', 'https://www.deezer.com/artist/1234'],
      ['applemusic', 'https://music.apple.com/us/artist/paramore/75950796'],
    ])
  })

  it('is empty for no ids', () => {
    expect(artistPlatformLinks({})).toEqual([])
    expect(artistPlatformLinks(undefined)).toEqual([])
  })
})
