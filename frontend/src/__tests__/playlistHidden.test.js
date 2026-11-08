import { describe, expect, it } from 'vitest'

import { buildPlaylists } from '../lib/library.js'

const row = (name, extra = {}) => ({
  name,
  files: [],
  count: 0,
  added: 1,
  cover: '',
  liked: false,
  manual: false,
  ...extra,
})

describe('buildPlaylists hidden songs', () => {
  it('carries how many songs the owner hid from an imported playlist', () => {
    const [plain, hiding] = buildPlaylists(
      [row('Mix'), row('Road trip', { hidden_count: 3 })],
      new Map()
    )
    expect(plain.hiddenCount).toBe(0)
    expect(hiding.hiddenCount).toBe(3)
  })

  it('gives a tracked playlist without an M3U none', () => {
    const [tracked] = buildPlaylists([], new Map(), [
      { playlist_name: 'Pending', spotify_playlist_id: 'sp1' },
    ])
    expect(tracked.hiddenCount).toBe(0)
  })
})
