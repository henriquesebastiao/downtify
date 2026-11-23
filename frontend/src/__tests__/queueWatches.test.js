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
  it("uses the artist's photo or the playlist watch's picture", () => {
    expect(watchCover(drake)).toBe('/api/artists/photo-proxy?name=Drake')
    // The Monitor's cover route: the saved file, else the service's cover.
    expect(watchCover(mix)).toBe('/api/monitor/playlists/2/cover')
    expect(watchCover({ id: 3, kind: 'playlist' })).toBe(
      '/api/monitor/playlists/3/cover'
    )
    expect(watchCover(null)).toBe('')
  })

  it('keeps the saved file for an event without the watch id', () => {
    expect(watchCover({ ...mix, id: undefined })).toBe(
      `/playlist-cover?file=${encodeURIComponent('Mix/2010s Mix.jpg')}`
    )
    expect(watchCover({ kind: 'playlist' })).toBe('')
  })
})
