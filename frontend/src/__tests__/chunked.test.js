import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getStreamChunk } = vi.hoisted(() => ({
  getStreamChunk: vi.fn(),
}))

vi.mock('/src/model/api', () => ({
  default: {
    getStreamChunk,
  },
}))

import {
  chunkIndexFor,
  clearChunkCache,
  createChunkSession,
  fetchChunk,
  prepareTrack,
} from '../model/chunked.js'

class FakeRanges {
  constructor() {
    this.list = []
  }

  get length() {
    return this.list.length
  }

  start(i) {
    return this.list[i][0]
  }

  end(i) {
    return this.list[i][1]
  }

  add(start, end) {
    this.list.push([start, end])
  }
}

class FakeSourceBuffer {
  constructor() {
    this.appended = []
    this.removed = []
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

  fire(event) {
    queueMicrotask(() => {
      this.updating = false
      ;(this.listeners[event] || []).forEach((fn) => fn())
    })
  }

  appendBuffer(data) {
    this.updating = true
    this.appended.push({ offset: this.timestampOffset, bytes: data.byteLength })
    this.fire('updateend')
  }

  remove(start, end) {
    this.updating = true
    this.removed.push([start, end])
    this.fire('updateend')
  }
}

class FakeMediaSource {
  constructor() {
    this.readyState = 'closed'
    this.duration = Number.NaN
    this.buffers = []
    this.listeners = {}
    this.ended = false
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
    const buffer = new FakeSourceBuffer()
    this.buffers.push(buffer)
    return buffer
  }

  endOfStream() {
    this.ended = true
    this.readyState = 'ended'
  }
}

function stubAudio() {
  return {
    src: '',
    currentTime: 0,
    play: vi.fn(() => Promise.resolve()),
    pause: vi.fn(),
    buffered: new FakeRanges(),
  }
}

function piece(bytes = 400000) {
  return new ArrayBuffer(bytes)
}

describe('chunkIndexFor', () => {
  it('maps seconds to 20-second pieces', () => {
    expect(chunkIndexFor(0)).toBe(0)
    expect(chunkIndexFor(19.9)).toBe(0)
    expect(chunkIndexFor(20)).toBe(1)
    expect(chunkIndexFor(65)).toBe(3)
  })
})

describe('createChunkSession', () => {
  beforeEach(() => {
    vi.resetModules()
    clearChunkCache()
    getStreamChunk.mockReset()
    getStreamChunk.mockImplementation(async (videoId, t) => ({
      data: piece(),
      start: t,
      duration: 200,
    }))
    globalThis.MediaSource = FakeMediaSource
    globalThis.URL.createObjectURL = () => 'blob:chunk'
    globalThis.URL.revokeObjectURL = () => {}
    globalThis.window = {
      innerWidth: 1280,
      location: { protocol: 'http:', hostname: 'localhost', port: '' },
    }
  })

  it('plays the first piece as soon as it lands', async () => {
    const audio = stubAudio()
    const session = createChunkSession(audio, {
      videoId: 'dQw4w9WgXcQ',
      total: 200,
    })
    await session.start()
    expect(audio.src).toBe('blob:chunk')
    expect(getStreamChunk).toHaveBeenCalledWith('dQw4w9WgXcQ', 0, {
      signal: expect.anything(),
    })
    expect(audio.play).toHaveBeenCalled()
    const [buffer] = session.media?.buffers || []
    expect(buffer).toBeTruthy()
  })

  it('fetches ahead while the piece plays', async () => {
    const audio = stubAudio()
    const session = createChunkSession(audio, {
      videoId: 'dQw4w9WgXcQ',
      total: 200,
    })
    await session.start()
    getStreamChunk.mockClear()
    session.ensureTime(18)
    await vi.waitFor(() => {
      expect(getStreamChunk).toHaveBeenCalledWith('dQw4w9WgXcQ', 20, {
        signal: expect.anything(),
      })
    })
  })

  it('jumps to an unloaded part with one fetch', async () => {
    const audio = stubAudio()
    const session = createChunkSession(audio, {
      videoId: 'dQw4w9WgXcQ',
      total: 200,
    })
    await session.start()
    audio.buffered.add(0, 20)
    getStreamChunk.mockClear()
    await session.seekTo(65)
    expect(getStreamChunk).toHaveBeenCalledWith('dQw4w9WgXcQ', 60, {
      signal: expect.anything(),
    })
    expect(audio.currentTime).toBe(65)
  })

  it('jumps inside loaded audio without fetching', async () => {
    const audio = stubAudio()
    const session = createChunkSession(audio, {
      videoId: 'dQw4w9WgXcQ',
      total: 200,
    })
    await session.start()
    audio.buffered.add(0, 20)
    getStreamChunk.mockClear()
    await session.seekTo(5)
    expect(getStreamChunk).not.toHaveBeenCalled()
    expect(audio.currentTime).toBe(5)
  })

  it('ends the stream once the tail lands', async () => {
    const audio = stubAudio()
    const session = createChunkSession(audio, {
      videoId: 'shortvid1234',
      total: 15,
    })
    await session.start()
    await vi.waitFor(() => {
      expect(session.media.ended).toBe(true)
    })
  })
})

describe('fetchChunk', () => {
  beforeEach(() => {
    clearChunkCache()
    getStreamChunk.mockReset()
    getStreamChunk.mockImplementation(async (videoId, t) => ({
      data: piece(),
      start: t,
      duration: 200,
    }))
  })

  it('remembers fetched pieces', async () => {
    await fetchChunk('dQw4w9WgXcQ', 0)
    await fetchChunk('dQw4w9WgXcQ', 0)
    expect(getStreamChunk).toHaveBeenCalledTimes(1)
  })
})

describe('prepareTrack', () => {
  beforeEach(() => {
    clearChunkCache()
    getStreamChunk.mockReset()
    getStreamChunk.mockImplementation(async (videoId, t) => ({
      data: piece(),
      start: t,
      duration: 200,
    }))
  })

  it('readies the video id, length and first piece', async () => {
    const ready = await prepareTrack({
      artist: 'Cher',
      name: 'Believe',
      youtube_id: 'dQw4w9WgXcQ',
    })
    expect(ready).toEqual({ videoId: 'dQw4w9WgXcQ', duration: 200 })
    // A later start reuses the cached first piece.
    await fetchChunk('dQw4w9WgXcQ', 0)
    expect(getStreamChunk).toHaveBeenCalledTimes(1)
  })
})
