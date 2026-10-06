import { describe, expect, it, vi } from 'vitest'

const { search, getStreamUrl, playList, playerState, findTrack } = vi.hoisted(
  () => ({
    search: vi.fn(),
    getStreamUrl: vi.fn(),
    playList: vi.fn(),
    playerState: { current: null, playing: false },
    findTrack: vi.fn(() => null),
  })
)

vi.mock('/src/model/api', () => ({
  default: {
    search,
    getStreamUrl,
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
import { videoIdFor } from '../model/streamResolve.js'

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
  it('plays the resolved URL as a transient player track', async () => {
    getStreamUrl.mockResolvedValueOnce({
      data: { url: 'https://r1---sn.googlevideo.com/x' },
    })
    const song = {
      ...SONG,
      youtube_id: 'dQw4w9WgXcQ',
      cover_url: 'https://img/xl',
    }
    await expect(playStream(song)).resolves.toBe(true)
    expect(getStreamUrl).toHaveBeenCalledWith('dQw4w9WgXcQ')
    expect(playList).toHaveBeenCalledOnce()
    const [tracks, options] = playList.mock.calls[0]
    expect(tracks).toHaveLength(1)
    expect(tracks[0]).toMatchObject({
      stream: true,
      video_id: 'dQw4w9WgXcQ',
      title: 'Believe',
      artist: 'Cher',
      cover: 'https://img/xl',
      url: 'https://r1---sn.googlevideo.com/x',
    })
    expect(options).toEqual({ context: null })
  })

  it('resolves false when the backend has no URL', async () => {
    playList.mockClear()
    getStreamUrl.mockResolvedValueOnce({ data: { url: '' } })
    await expect(
      playStream({ ...SONG, youtube_id: 'dQw4w9WgXcQ' })
    ).resolves.toBe(false)
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
