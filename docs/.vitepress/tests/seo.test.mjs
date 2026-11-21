import { describe, expect, it } from 'vitest'
import { llmsText } from '../lib/llms.mjs'
import {
  faqEntries,
  homeGraph,
  jsonLdTag,
  OG_LOCALE,
  pageGraph,
  plainText,
} from '../lib/seo.mjs'
import { LOCALES } from '../locales/index.mjs'

describe('plainText', () => {
  it('keeps the words of links, code and emphasis', () => {
    expect(
      plainText('See [Lyrics](features/lyrics.md), `yt-dlp` and **bold** _it_.')
    ).toBe('See Lyrics, yt-dlp and bold it.')
  })

  it('drops tags and collapses whitespace', () => {
    expect(plainText('<b>Hi</b>\n\n  there')).toBe('Hi there')
  })
})

describe('faqEntries', () => {
  it('reads ::: details callouts as questions and answers', () => {
    const source = [
      '## Questions',
      '',
      '::: details Do I need an API key?',
      'No. See [How it works](how-it-works.md).',
      ':::',
      '',
      '::: tip',
      'Not a question.',
      ':::',
      '',
      '::: details Does it run on `arm64`?',
      'Yes.',
      ':::',
    ].join('\n')
    expect(faqEntries(source)).toEqual([
      { question: 'Do I need an API key?', answer: 'No. See How it works.' },
      { question: 'Does it run on arm64?', answer: 'Yes.' },
    ])
  })
})

describe('structured data', () => {
  const site = 'https://example.org/'

  it('describes the app, its video and its questions on a home page', () => {
    const data = homeGraph({
      site,
      url: site,
      lang: 'en-US',
      languages: ['en-US'],
      siteDescription: 'Docs',
      description: 'A downloader',
      version: '1.2.3',
      downloadUrl: 'https://example.org/download',
      installUrl: 'https://example.org/install/',
      repository: 'https://github.com/x/y',
      image: 'https://example.org/og.png',
      screenshots: [],
      features: ['One'],
      video: {
        name: 'Demo',
        description: 'A demo',
        thumbnail: 'https://example.org/poster.webp',
        content: 'https://example.org/demo.mp4',
        uploaded: '2026-01-01T00:00:00Z',
        duration: 'PT10S',
      },
      faq: [{ question: 'Q?', answer: 'A.' }],
    })
    const types = data['@graph'].map((node) => node['@type'])
    expect(types).toEqual([
      'Person',
      'WebSite',
      'SoftwareApplication',
      'VideoObject',
      'FAQPage',
    ])
    const app = data['@graph'][2]
    expect(app.softwareVersion).toBe('1.2.3')
    expect(app.offers.price).toBe('0')
  })

  it('gives a page its breadcrumbs', () => {
    const data = pageGraph({
      site,
      url: `${site}features/player/`,
      lang: 'en-US',
      title: 'Player',
      description: 'Plays music',
      image: `${site}og.png`,
      crumbs: [
        { name: 'Home', url: site },
        { name: 'Player', url: `${site}features/player/` },
      ],
    })
    const crumbs = data['@graph'][1]
    expect(crumbs['@type']).toBe('BreadcrumbList')
    expect(crumbs.itemListElement.map((item) => item.position)).toEqual([1, 2])
  })

  it('cannot close its <script> early', () => {
    const [, , json] = jsonLdTag({ text: '</script><script>alert(1)' })
    expect(json).not.toContain('</script>')
    expect(JSON.parse(json).text).toBe('</script><script>alert(1)')
  })

  it('has an Open Graph locale for every language', () => {
    expect(Object.keys(OG_LOCALE).sort()).toEqual(Object.keys(LOCALES).sort())
  })
})

describe('llmsText', () => {
  it('lists every sidebar page under its group', () => {
    const text = llmsText({
      site: 'https://example.org/',
      nav: [
        { title: 'Home', page: 'index.md' },
        { title: 'Group', items: [{ title: 'Page', page: 'a.md' }] },
      ],
      titles: { groups: { Group: 'Group' }, pages: { 'a.md': 'A page' } },
      url: (page) => `https://example.org/${page}`,
      describe: (page) => `About ${page}`,
      summary: 'A downloader.',
      version: '1.0.0',
    })
    expect(text).toMatch(/^# Downtify\n\n> A downloader\.\n/)
    expect(text).toContain(
      '## Group\n\n- [A page](https://example.org/a.md): About a.md'
    )
    expect(text).toContain(
      '## Documentation\n\n- [Home](https://example.org/index.md)'
    )
  })
})
