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

  it('chains the next page from the last row', async () => {
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: ROWS },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', 'Believe')
    expect(similar.hasMore.value).toBe(true)
    const next = {
      song_id: 'v2',
      name: 'The Power',
      artists: ['Cher'],
      artist: 'Cher',
      cover_url: 'https://img/v2',
      duration: 200,
      url: 'https://music.youtube.com/watch?v=v2',
      match: 0.8,
    }
    getSimilarTracks.mockResolvedValueOnce({
      data: { tracks: [next, ROWS[0]] },
    })
    const added = await similar.loadMore()
    expect(getSimilarTracks).toHaveBeenLastCalledWith('Cher', 'Strong Enough')
    expect(added).toEqual([next])
    expect(similar.songs.value).toHaveLength(2)
    expect(similar.hasMore.value).toBe(true)
  })

  it('ends the list when a page adds nothing new', async () => {
    getSimilarTracks.mockResolvedValueOnce({ data: { tracks: [] } })
    const similar = useSimilar()
    const added = await similar.loadMore()
    expect(added).toEqual([])
    expect(similar.hasMore.value).toBe(false)
  })

  it('restarts the endless list on a new search', async () => {
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: ROWS },
    })
    const similar = useSimilar()
    expect(similar.hasMore.value).toBe(false)
    await similar.searchFor('Cher', 'Believe')
    expect(similar.hasMore.value).toBe(true)
    expect(similar.songs.value).toHaveLength(1)
  })
})
