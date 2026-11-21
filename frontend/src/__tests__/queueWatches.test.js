import { describe, expect, it } from 'vitest'
import { queueWatches, watchCover } from '/src/lib/queueWatches'

const drake = { id: 1, name: 'Drake', kind: 'artist' }
const mix = {
  id: 2,
  name: '2010s Mix',
  kind: 'playlist',
  cover_file: 'Mix/2010s Mix.jpg',
}

describe('queueWatches', () => {
  it('counts songs per watch, most first, ignoring songs no watch asked for', () => {
    const rows = queueWatches([
      { watch: mix, state: 'done' },
      { watch: drake, state: 'active' },
      { watch: drake, state: 'queued' },
      { watch: drake, state: 'done' },
      { state: 'active' },
    ])
    expect(rows.map((r) => [r.watch.name, r.count, r.waiting])).toEqual([
      ['Drake', 3, 2],
      ['2010s Mix', 1, 0],
    ])
  })
})

describe('watchCover', () => {
  it("uses the artist's photo or the playlist's saved cover", () => {
    expect(watchCover(drake)).toBe('/api/artists/photo-proxy?name=Drake')
    expect(watchCover(mix)).toBe(
      `/playlist-cover?file=${encodeURIComponent('Mix/2010s Mix.jpg')}`
    )
    expect(watchCover({ id: 3, kind: 'playlist' })).toBe('')
    expect(watchCover(null)).toBe('')
  })
})
