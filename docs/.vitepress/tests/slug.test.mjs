import { describe, expect, it } from 'vitest'
import { slugify, slugifyWithState, unique } from '../lib/slug.mjs'

// Expected values are the ids zensical (Python-Markdown `toc`) generated
// for these headings, so deep links into the old site keep working.
describe('slugify', () => {
  it.each([
    ['GET /api/url/resolve', 'get-apiurlresolve'],
    [
      'DELETE /api/playlists/batches/{spotify_playlist_id}',
      'delete-apiplaylistsbatchesspotify_playlist_id',
    ],
    ["One command and you're done", 'one-command-and-youre-done'],
    ['slskd & Navidrome', 'slskd-navidrome'],
    [
      '2. Audio match — YouTube Music, then YouTube',
      '2-audio-match-youtube-music-then-youtube',
    ],
    ['Português (Brasil)', 'portugues-brasil'],
    ['  Spaces   and --- dashes ', 'spaces-and-dashes'],
  ])('%s', (text, id) => {
    expect(slugify(text)).toBe(id)
  })
})

describe('unique', () => {
  it('numbers repeats with an underscore', () => {
    const used = new Set()
    expect(unique('setup', used)).toBe('setup')
    expect(unique('setup', used)).toBe('setup_1')
    expect(unique('setup', used)).toBe('setup_2')
  })

  it('never returns an empty id', () => {
    expect(unique('', new Set())).toBe('_1')
  })
})

describe('slugifyWithState', () => {
  it('keeps ids unique per page, not across pages', () => {
    const page1 = { env: {} }
    const page2 = { env: {} }
    expect(slugifyWithState('Setup', page1)).toBe('setup')
    expect(slugifyWithState('Setup', page1)).toBe('setup_1')
    expect(slugifyWithState('Setup', page2)).toBe('setup')
  })
})
