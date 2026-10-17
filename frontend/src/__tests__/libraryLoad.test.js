import { describe, expect, it, vi } from 'vitest'

const { getLibrarySummary, listPlaylists, getPlaylistBatches } = vi.hoisted(
  () => ({
    getLibrarySummary: vi.fn(),
    listPlaylists: vi.fn(),
    getPlaylistBatches: vi.fn(),
  })
)

vi.mock('/src/model/api', () => ({
  default: {
    onMessage: () => () => {},
    getLibrarySummary,
    listPlaylists,
    getPlaylistBatches,
  },
}))

vi.mock('/src/model/player', () => ({
  usePlayer: () => ({ refreshTracks: () => {}, forgetFiles: () => {} }),
}))

import { useLibrary } from '../model/library.js'

describe('load', () => {
  it('does not wait on the slow playlist batch reports', async () => {
    // GET /api/playlists/batches checks every tracked Spotify track
    // against the disk - seconds on a large library - and only adds
    // badges, so the Library must show without it.
    getLibrarySummary.mockResolvedValue({
      data: { track_count: 3, recent_albums: [] },
    })
    listPlaylists.mockResolvedValue({ data: [] })
    let answerBatches
    getPlaylistBatches.mockReturnValue(
      new Promise((resolve) => {
        answerBatches = resolve
      })
    )

    const library = useLibrary()
    await library.load({ force: true })

    expect(library.loaded.value).toBe(true)
    expect(library.trackCount.value).toBe(3)
    expect(library.batches.value).toEqual([])
    expect(getPlaylistBatches).toHaveBeenCalledTimes(1)

    const report = { spotify_playlist_id: 'abc', status: 'complete' }
    answerBatches({ data: { playlists: [report] } })
    await vi.waitFor(() => {
      expect(library.batches.value).toEqual([report])
    })
  })

  it('keeps the library usable when batch reports fail', async () => {
    getLibrarySummary.mockResolvedValue({ data: { track_count: 1 } })
    listPlaylists.mockResolvedValue({ data: [] })
    getPlaylistBatches.mockRejectedValue(new Error('boom'))

    const library = useLibrary()
    await library.load({ force: true })

    expect(library.loaded.value).toBe(true)
    expect(library.error.value).toBe('')
  })
})
