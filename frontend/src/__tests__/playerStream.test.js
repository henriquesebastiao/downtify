import { beforeEach, describe, expect, it, vi } from 'vitest'

const { resolveTrackUrl } = vi.hoisted(() => ({
  resolveTrackUrl: vi.fn(),
}))

vi.mock('/src/model/streamResolve', () => ({ resolveTrackUrl }))

const audios = vi.hoisted(() => ({ list: [] }))

function stubAudio() {
  const audio = {
    src: '',
    currentTime: 0,
    duration: 0,
    volume: 1,
    playbackRate: 1,
    muted: false,
    play: vi.fn(() => Promise.resolve()),
    pause: vi.fn(),
    removeAttribute: vi.fn((name) => {
      if (name === 'src') audio.src = ''
    }),
    addEventListener: vi.fn(),
    load: vi.fn(),
  }
  audios.list.push(audio)
  return audio
}

const lib = (title) => ({
  file: `${title}.mp3`,
  title,
  artist: 'Artist',
  url: `/downloads/${title}.mp3`,
})

const pending = (title) => ({
  file: '',
  stream: true,
  title,
  artist: 'Artist',
  url: '',
})

describe('streaming in the player queue', () => {
  let player

  beforeEach(async () => {
    vi.resetModules()
    audios.list.length = 0
    resolveTrackUrl.mockReset()
    resolveTrackUrl.mockImplementation(async (track) => ({
      url: `https://stream.example/${encodeURIComponent(track.title)}`,
    }))
    globalThis.window = {
      innerWidth: 1280,
      addEventListener: () => {},
      location: { protocol: 'http:', hostname: 'localhost', port: '' },
    }
    globalThis.localStorage = {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    }
    globalThis.Audio = function () {
      return stubAudio()
    }
    const mod = await import('../model/player.js')
    player = mod.usePlayer()
  })

  it('resolves an unstored track before playing it', async () => {
    player.playList([pending('B')])
    await vi.waitFor(() => {
      expect(audios.list[0].play).toHaveBeenCalled()
    })
    expect(audios.list[0].src).toBe('https://stream.example/B')
    expect(player.currentTrack.value.url).toBe('https://stream.example/B')
    expect(player.playError.value).toBe('')
  })

  it('keeps one track ahead resolved while the current one plays', async () => {
    player.playList([lib('A'), pending('B'), pending('C')])
    await vi.waitFor(() => {
      expect(player.playlist.value[1].url).toBe('https://stream.example/B')
    })
    // Only one ahead: the third waits its turn.
    expect(player.playlist.value[2].url).toBe('')
    expect(audios.list[0].src).toBe('/downloads/A.mp3')
  })

  it('advances past an unresolvable track to the next one', async () => {
    resolveTrackUrl.mockImplementation(async (track) => {
      if (track.title === 'Bad') throw new Error('nomatch')
      return { url: `https://stream.example/${track.title}` }
    })
    player.playList([pending('Bad'), pending('Good')])
    await vi.waitFor(() => {
      expect(audios.list[0].src).toBe('https://stream.example/Good')
    })
    expect(player.currentTrack.value.title).toBe('Good')
  })

  it('gives up with an error after repeated failures', async () => {
    resolveTrackUrl.mockRejectedValue(new Error('down'))
    player.playList([pending('A'), pending('B'), pending('C')])
    await vi.waitFor(() => {
      expect(player.playError.value).toBe('unplayable')
    })
    expect(player.isPlaying.value).toBe(false)
  })

  it('never persists a queue holding a stream', async () => {
    const setItem = vi.fn()
    globalThis.localStorage = {
      getItem: () => null,
      setItem,
      removeItem: () => {},
    }
    player.playList([lib('A'), pending('B')])
    await vi.waitFor(() => {
      expect(player.playlist.value[1].url).toBe('https://stream.example/B')
    })
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(
      setItem.mock.calls.some(([key]) => key === 'downtify-player-session')
    ).toBe(false)
  })
})
