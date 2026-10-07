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
    song_id: 'v1',
    name: 'Strong Enough',
    artists: ['Cher'],
    artist: 'Cher',
    cover_url: 'https://img/v1',
    duration: 224,
    url: 'https://music.youtube.com/watch?v=v1',
    match: 0.9,
  },
]

describe('useSimilar', () => {
  it('maps rows to downloadable songs', async () => {
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: ROWS },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    expect(getSimilarTracks).toHaveBeenCalledWith('Cher', 'Believe')
    expect(similar.songs.value).toEqual([
      {
        song_id: 'v1',
        name: 'Strong Enough',
        artists: ['Cher'],
        artist: 'Cher',
        cover_url: 'https://img/v1',
        duration: 224,
        url: 'https://music.youtube.com/watch?v=v1',
        match: 0.9,
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
      response: { data: { detail: 'YouTube Music did not answer' } },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    expect(similar.tracks.value).toEqual([])
    expect(similar.error.value).toBe('YouTube Music did not answer')
  })
})
