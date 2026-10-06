import { beforeEach, describe, expect, it, vi } from 'vitest'

const { resolveTrackUrl, chunkingSupported, getStreamChunk } = vi.hoisted(
  () => ({
    resolveTrackUrl: vi.fn(),
    chunkingSupported: vi.fn(() => false),
    getStreamChunk: vi.fn(),
  })
)

vi.mock('/src/model/streamResolve', () => ({
  resolveTrackUrl,
  videoIdFor: async () => 'dQw4w9WgXcQ',
}))

// The real chunk engine, except for support detection (per-test).
vi.mock('/src/model/chunked', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, chunkingSupported: (...args) => chunkingSupported(...args) }
})

vi.mock('/src/model/api', () => ({
  default: {
    getStreamChunk,
  },
}))

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

class FakeSourceBuffer {
  constructor() {
    this.appended = []
    this.updating = false
    this.timestampOffset = 0
    this.listeners = {}
  }

  addEventListener(event, fn) {
    ;(this.listeners[event] ||= []).push(fn)
  }

  removeEventListener(event, fn) {
    this.listeners[event] = (this.listeners[event] || []).filter(
      (f) => f !== fn
    )
  }

  appendBuffer(data) {
    this.updating = true
    this.appended.push(data.byteLength)
    queueMicrotask(() => {
      this.updating = false
      ;(this.listeners.updateend || []).forEach((fn) => fn())
    })
  }

  remove() {
    queueMicrotask(() =>
      (this.listeners.updateend || []).forEach((fn) => fn())
    )
  }
}

class FakeMediaSource {
  constructor() {
    this.readyState = 'closed'
    this.duration = Number.NaN
    this.listeners = {}
  }

  addEventListener(event, fn) {
    ;(this.listeners[event] ||= []).push(fn)
    if (event === 'sourceopen' && this.readyState === 'closed') {
      this.readyState = 'open'
      queueMicrotask(() => this.listeners[event].forEach((f) => f()))
    }
  }

  removeEventListener(event, fn) {
    this.listeners[event] = (this.listeners[event] || []).filter(
      (f) => f !== fn
    )
  }

  addSourceBuffer() {
    return new FakeSourceBuffer()
  }

  endOfStream() {
    this.readyState = 'ended'
  }

  static isTypeSupported() {
    return true
  }
}

describe('streaming in the player queue', () => {
  let player

  beforeEach(async () => {
    vi.resetModules()
    audios.list.length = 0
    chunkingSupported.mockReturnValue(false)
    resolveTrackUrl.mockReset()
    resolveTrackUrl.mockImplementation(async (track) => ({
      url: `https://stream.example/${encodeURIComponent(track.title)}`,
    }))
    getStreamChunk.mockReset()
    getStreamChunk.mockResolvedValue({
      data: new ArrayBuffer(1000),
      start: 0,
      duration: 200,
    })
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

  it('plays piece by piece when the browser supports it', async () => {
    chunkingSupported.mockReturnValue(true)
    globalThis.MediaSource = FakeMediaSource
    globalThis.URL.createObjectURL = () => 'blob:chunk'
    globalThis.URL.revokeObjectURL = () => {}
    player.playList([pending('B')])
    await vi.waitFor(() => {
      expect(audios.list[0].play).toHaveBeenCalled()
    })
    expect(audios.list[0].src).toBe('blob:chunk')
    expect(player.playlist.value[0].video_id).toBe('dQw4w9WgXcQ')
    expect(player.playError.value).toBe('')
  })
})
