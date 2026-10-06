import { describe, expect, it, vi } from 'vitest'

const { getSimilarTracks } = vi.hoisted(() => ({
  getSimilarTracks: vi.fn(),
}))

vi.mock('/src/model/api', () => ({
  default: {
    onUnauthorized: () => () => {},
    onForbidden: () => () => {},
    getAuthStatus: () =>
      Promise.resolve({ data: { signed_in: true, user: { role: 'admin' } } }),
    onMessage: () => () => {},
    getSettings: () => Promise.resolve({ data: {} }),
    lookupLibrarySongs: () => Promise.resolve({ data: [] }),
    getSimilarTracks,
  },
}))

import { useSimilar } from '../model/similar'

const ROWS = [
  {
    title: 'Believe',
    artist: 'Cher',
    match: 0.95,
    url: 'https://www.last.fm/music/Cher/_/Believe',
    image_url: 'https://img/xl',
  },
]

describe('useSimilar', () => {
  it('maps Last.fm rows to previewable songs', async () => {
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: ROWS },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    expect(getSimilarTracks).toHaveBeenCalledWith('Cher', 'Believe')
    expect(similar.songs.value).toEqual([
      {
        name: 'Believe',
        artists: ['Cher'],
        artist: 'Cher',
        cover_url: 'https://img/xl',
        match: 0.95,
        lastfm_url: 'https://www.last.fm/music/Cher/_/Believe',
      },
    ])
    expect(similar.error.value).toBe('')
  })

  it('does not ask without both fields', async () => {
    getSimilarTracks.mockClear()
    const similar = useSimilar()
    await similar.searchFor('Cher', '  ')
    expect(getSimilarTracks).not.toHaveBeenCalled()
    expect(similar.searched.value).toBe(false)
  })

  it('reports a backend failure', async () => {
    getSimilarTracks.mockRejectedValueOnce({
      response: { data: { detail: 'No Last.fm API key' } },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    expect(similar.tracks.value).toEqual([])
    expect(similar.error.value).toBe('No Last.fm API key')
  })
})
