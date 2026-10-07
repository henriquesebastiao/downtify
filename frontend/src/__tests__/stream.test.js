import { describe, expect, it, vi } from 'vitest'

const { search, playList, playerState, findTrack } = vi.hoisted(() => ({
  search: vi.fn(),
  playList: vi.fn(),
  playerState: { current: null, playing: false },
  findTrack: vi.fn(() => null),
}))

vi.mock('/src/model/api', () => ({
  default: {
    search,
  },
}))

vi.mock('/src/model/player', () => ({
  usePlayer: () => ({
    playList,
    currentTrack: {
      get value() {
        return playerState.current
      },
    },
    isPlaying: {
      get value() {
        return playerState.playing
      },
    },
  }),
}))

vi.mock('/src/model/library', () => ({
  useLibrary: () => ({ findTrack }),
}))

import { isStreamingSong, playStream } from '../model/stream.js'
import { resolveTrackUrl, videoIdFor } from '../model/streamResolve.js'

describe('resolveTrackUrl', () => {
  it('points at the server cache, never at YouTube', async () => {
    await expect(
      resolveTrackUrl({ ...SONG, youtube_id: 'dQw4w9WgXcQ' })
    ).resolves.toEqual({
      url: '/api/stream/file?video_id=dQw4w9WgXcQ',
      videoId: 'dQw4w9WgXcQ',
    })
  })
})

const SONG = { name: 'Believe', artists: ['Cher'] }

describe('videoIdFor', () => {
  it('takes the row’s own video id first', async () => {
    await expect(
      videoIdFor({ ...SONG, youtube_id: 'dQw4w9WgXcQ' })
    ).resolves.toBe('dQw4w9WgXcQ')
    await expect(videoIdFor({ ...SONG, song_id: 'dQw4w9WgXcQ' })).resolves.toBe(
      'dQw4w9WgXcQ'
    )
    expect(search).not.toHaveBeenCalled()
  })

  it('falls back to the first search hit with a video id', async () => {
    search.mockResolvedValueOnce({
      data: [
        { name: 'Believe', artists: ['Tribute Band'] },
        { name: 'Believe', artists: ['Cher'], song_id: 'abc123DEFGH' },
      ],
    })
    await expect(videoIdFor(SONG)).resolves.toBe('abc123DEFGH')
    expect(search).toHaveBeenCalledWith('Cher Believe')
  })

  it('fails when nothing resolves', async () => {
    search.mockResolvedValueOnce({ data: [] })
    await expect(videoIdFor(SONG)).rejects.toThrow()
  })
})

describe('playStream', () => {
  it('plays the server file URL as a transient player track', async () => {
    const song = {
      ...SONG,
      youtube_id: 'dQw4w9WgXcQ',
      cover_url: 'https://img/xl',
    }
    await expect(playStream(song)).resolves.toBe(true)
    // The browser never touches YouTube: the server caches and serves
    // (no direct-URL call happens at all).
    expect(playList).toHaveBeenCalledOnce()
    const [tracks, options] = playList.mock.calls[0]
    expect(tracks).toHaveLength(1)
    expect(tracks[0]).toMatchObject({
      stream: true,
      video_id: 'dQw4w9WgXcQ',
      title: 'Believe',
      artist: 'Cher',
      cover: 'https://img/xl',
      url: '/api/stream/file?video_id=dQw4w9WgXcQ',
    })
    expect(options).toEqual({ context: null })
  })

  it('resolves false when nothing resolves to a video', async () => {
    playList.mockClear()
    search.mockResolvedValueOnce({ data: [] })
    await expect(playStream(SONG)).resolves.toBe(false)
    expect(playList).not.toHaveBeenCalled()
  })

  it('resolves false without artist and title', async () => {
    await expect(playStream({ name: '' })).resolves.toBe(false)
  })
})

describe('isStreamingSong', () => {
  it('matches the player’s transient track by video id', () => {
    playerState.current = {
      stream: true,
      video_id: 'dQw4w9WgXcQ',
      artist: 'Cher',
      title: 'Believe',
    }
    expect(isStreamingSong({ ...SONG, youtube_id: 'dQw4w9WgXcQ' })).toBe(true)
    expect(isStreamingSong({ ...SONG, youtube_id: 'other123456' })).toBe(false)
    playerState.current = null
    expect(isStreamingSong({ ...SONG, youtube_id: 'dQw4w9WgXcQ' })).toBe(false)
  })

  it('matches by artist and title when the row has no video id', () => {
    playerState.current = {
      stream: true,
      video_id: 'abc123DEFGH',
      artist: 'Cher',
      title: 'Believe',
    }
    expect(isStreamingSong(SONG)).toBe(true)
    expect(isStreamingSong({ name: 'Other', artists: ['Cher'] })).toBe(false)
    playerState.current = {
      file: 'Cher - Believe.mp3',
      artist: 'Cher',
      title: 'Believe',
    }
    expect(isStreamingSong(SONG)).toBe(false)
  })
})
