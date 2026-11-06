import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getSimilarTracks, getLocalSimilar } = vi.hoisted(() => ({
  getSimilarTracks: vi.fn(),
  getLocalSimilar: vi.fn(),
}))

vi.mock('/src/model/musicAI', async () => {
  const { ref } = await import('vue')
  return {
    musicAI: {
      capabilities: ref({
        features: { external_beta: true, similarity: true },
      }),
      refresh: vi.fn(),
      externalSimilar: getSimilarTracks,
      similar: getLocalSimilar,
    },
  }
})

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
import { musicAI } from '/src/model/musicAI'
import { nextTick } from 'vue'

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
  beforeEach(async () => {
    musicAI.capabilities.value = { features: { external_beta: true, similarity: true } }
    await nextTick()
    useSimilar().setSource('external')
  })
  it('hides both search commands and makes no request when both modules are disabled', async () => {
    musicAI.capabilities.value = { features: { external_beta: false, similarity: false } }
    await nextTick()
    getSimilarTracks.mockClear()
    getLocalSimilar.mockClear()
    const similar = useSimilar()
    expect(similar.canSearch.value).toBe(false)
    await similar.searchFor('Synthetic artist', 'Synthetic title')
    expect(getSimilarTracks).not.toHaveBeenCalled()
    expect(getLocalSimilar).not.toHaveBeenCalled()
  })
  it('chooses the only enabled source without exposing the other command', async () => {
    musicAI.capabilities.value = { features: { external_beta: true, similarity: false } }
    await nextTick()
    const similar = useSimilar()
    expect(similar.source.value).toBe('external')
    expect(similar.localEnabled.value).toBe(false)
    expect(similar.canSearch.value).toBe(true)
    musicAI.capabilities.value = { features: { external_beta: false, similarity: true } }
    await nextTick()
    expect(similar.source.value).toBe('local')
    expect(similar.externalEnabled.value).toBe(false)
  })
  it('keeps a local request entirely inside the local catalog', async () => {
    const similar = useSimilar()
    similar.setSource('local')
    getSimilarTracks.mockClear()
    getLocalSimilar.mockResolvedValueOnce({
      data: {
        tracks: [
          {
            song_id: 'local-one',
            file: 'one.flac',
            name: 'One',
            artist: 'A',
            source: 'library',
          },
        ],
      },
    })
    await similar.searchFor('A', 'Seed')
    expect(getLocalSimilar).toHaveBeenCalledWith('A', 'Seed')
    expect(getSimilarTracks).not.toHaveBeenCalled()
    expect(similar.songs.value[0].source).toBe('library')
    expect(similar.hasMore.value).toBe(false)
  })
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
        album_name: '',
        cover_url: 'https://img/v1',
        duration: 224,
        url: 'https://music.youtube.com/watch?v=v1',
        match: 0.9,
      },
    ])
    expect(similar.error.value).toBe('')
  })

  it('does not ask without either field', async () => {
    getSimilarTracks.mockClear()
    const similar = useSimilar()
    await similar.searchFor('  ', '  ')
    expect(getSimilarTracks).not.toHaveBeenCalled()
    expect(similar.searched.value).toBe(false)
  })

  it('asks with only the artist', async () => {
    getSimilarTracks.mockClear()
    getSimilarTracks.mockResolvedValueOnce({
      data: { artist: 'Cher', track: 'Believe', tracks: ROWS },
    })
    const similar = useSimilar()
    await similar.searchFor('Cher', '  ')
    expect(getSimilarTracks).toHaveBeenCalledWith('Cher', '')
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
