import { describe, expect, it } from 'vitest'
import { pageRoute, resolveSourceLink, rewritePage } from '../lib/routes.mjs'

describe('rewritePage', () => {
  it('writes pages as <name>/index.md', () => {
    expect(rewritePage('features/player.md')).toBe('features/player/index.md')
    expect(rewritePage('changelog.md')).toBe('changelog/index.md')
  })

  it('leaves index and 404 pages alone', () => {
    expect(rewritePage('index.md')).toBe('index.md')
    expect(rewritePage('features/index.md')).toBe('features/index.md')
    expect(rewritePage('404.md')).toBe('404.md')
  })
})

describe('pageRoute', () => {
  it('uses trailing-slash URLs', () => {
    expect(pageRoute('index.md')).toBe('/')
    expect(pageRoute('features/index.md')).toBe('/features/')
    expect(pageRoute('features/player.md')).toBe('/features/player/')
  })
})

describe('resolveSourceLink', () => {
  it('resolves relative .md links against the source page', () => {
    expect(resolveSourceLink('lyrics.md', 'features')).toBe('/features/lyrics/')
    expect(resolveSourceLink('../api-reference.md#library', 'features')).toBe(
      '/api-reference/#library'
    )
    expect(resolveSourceLink('features/index.md', '.')).toBe('/features/')
    expect(resolveSourceLink('installation.md?x=1#a', 'getting-started')).toBe(
      '/getting-started/installation/?x=1#a'
    )
  })

  it('leaves other links alone', () => {
    for (const href of [
      '#section',
      '/features/player/',
      'https://example.com/a.md',
      'mailto:me@example.com',
      '//cdn.example.com/x.md',
      'assets/logo.svg',
      '../../outside.md',
      '',
    ]) {
      expect(resolveSourceLink(href, 'features')).toBeNull()
    }
  })
})
