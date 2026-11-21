import { computed, nextTick, reactive, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  STAGE_PING_MS,
  STAGE_TIMEOUT_MS,
  stageChannelName,
  stagePath,
  stageState,
} from '../lib/karaokeStage'

const player = vi.hoisted(() => ({}))
vi.mock('/src/model/player', () => ({ usePlayer: () => player }))

// Delivers to the other channels of the same name, like the real one.
const open = new Map()
class FakeChannel {
  constructor(name) {
    this.name = name
    if (!open.has(name)) open.set(name, new Set())
    open.get(name).add(this)
  }
  postMessage(message) {
    const data = structuredClone(message)
    for (const other of open.get(this.name)) {
      if (other !== this) other.onmessage?.({ data })
    }
  }
  close() {
    open.get(this.name).delete(this)
  }
}

const song = {
  file: 'a.mp3',
  title: 'A',
  artist: 'X',
  cover: '/c',
  hasCover: 1,
}
let store
let openWindow

function resetPlayer() {
  player.currentTrack = ref(song)
  player.currentTime = ref(12)
  player.isPlaying = ref(true)
  const upcoming = ref([{ track: { file: 'b.mp3', title: 'B' } }])
  player.upcoming = computed(() => upcoming.value)
}

async function host() {
  vi.resetModules()
  const { useKaraokeStage } = await import('../model/karaokeStage')
  return useKaraokeStage()
}

async function stage(id) {
  const { connectToHost } = await import('../model/karaokeStageMirror')
  return connectToHost(id)
}

function hostId() {
  return [...store.values()][0]
}

beforeEach(() => {
  vi.useFakeTimers()
  open.clear()
  store = new Map()
  openWindow = vi.fn(() => ({ closed: false, focus: vi.fn() }))
  vi.stubGlobal('BroadcastChannel', FakeChannel)
  vi.stubGlobal('sessionStorage', {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
  })
  vi.stubGlobal('window', {
    location: { protocol: 'http:', hostname: 'x', port: '' },
    open: openWindow,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })
  resetPlayer()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('stageState', () => {
  it('can be posted even when built from reactive tracks', () => {
    const state = stageState({
      track: reactive({ ...song, extra: { nested: true } }),
      next: null,
      time: 3,
      playing: true,
    })
    expect(structuredClone(state)).toEqual({
      type: 'state',
      track: {
        file: 'a.mp3',
        title: 'A',
        artist: 'X',
        album: '',
        cover: '/c',
        hasCover: true,
      },
      next: null,
      time: 3,
      playing: true,
    })
  })

  it('has no track when nothing is loaded', () => {
    expect(stageState({ track: null }).track).toBeNull()
  })
})

describe('stagePath', () => {
  it('names the host and honours the base URL', () => {
    expect(stagePath('', 'a b')).toBe('/karaoke.html?host=a%20b')
    expect(stagePath('/app', 'x')).toBe('/app/karaoke.html?host=x')
  })
})

describe('the projected window', () => {
  it('opens one named popup and reuses the host id', async () => {
    const karaoke = await host()
    expect(karaoke.open()).toBe(true)
    karaoke.open()
    const [url, name, features] = openWindow.mock.calls[0]
    expect(url).toBe(`/karaoke.html?host=${hostId()}`)
    expect(name).toContain(hostId())
    expect(features).toContain('popup')
    expect(openWindow.mock.calls[1][1]).toBe(name)
  })

  it('reports a blocked popup', async () => {
    openWindow.mockReturnValue(null)
    const karaoke = await host()
    expect(karaoke.open()).toBe(false)
  })

  it('brings an open window forward instead of opening another', async () => {
    const karaoke = await host()
    karaoke.open()
    const mirror = await stage(hostId())
    const opened = openWindow.mock.results[0].value
    opened.focus.mockClear()
    karaoke.open()
    expect(openWindow).toHaveBeenCalledTimes(1)
    expect(opened.focus).toHaveBeenCalled()
    mirror.stop()
  })

  it('shows what the main window is playing as soon as it connects', async () => {
    const karaoke = await host()
    karaoke.open()
    const mirror = await stage(hostId())
    expect(karaoke.connected.value).toBe(true)
    expect(mirror.currentTrack.value.file).toBe('a.mp3')
    expect(mirror.nextTrack.value.file).toBe('b.mp3')
    expect(mirror.currentTime.value).toBe(12)
    expect(mirror.isPlaying.value).toBe(true)
    mirror.stop()
  })

  it('follows a song picked in the main window', async () => {
    const karaoke = await host()
    karaoke.open()
    const mirror = await stage(hostId())
    player.currentTrack.value = { file: 'c.mp3', title: 'C' }
    player.currentTime.value = 0
    await nextTick()
    expect(mirror.currentTrack.value.file).toBe('c.mp3')
    expect(mirror.currentTime.value).toBe(0)
    mirror.stop()
  })

  it('follows the clock and pausing', async () => {
    const karaoke = await host()
    karaoke.open()
    const mirror = await stage(hostId())
    player.currentTime.value = 40
    player.isPlaying.value = false
    await nextTick()
    expect(mirror.currentTime.value).toBe(40)
    expect(mirror.isPlaying.value).toBe(false)
    mirror.stop()
  })

  it('sends nothing while no window is connected', async () => {
    const karaoke = await host()
    karaoke.open()
    const post = vi.spyOn(FakeChannel.prototype, 'postMessage')
    player.currentTime.value = 50
    await nextTick()
    expect(post).not.toHaveBeenCalled()
    post.mockRestore()
  })

  it('finds an open window again after the main one reloads', async () => {
    const first = await host()
    first.open()
    const id = hostId()
    const mirror = await stage(id)
    const [oldHost] = open.get(stageChannelName(id))
    oldHost.close()

    const reloaded = await host()
    reloaded.resume()
    expect(reloaded.connected.value).toBe(false)
    vi.advanceTimersByTime(STAGE_PING_MS)
    expect(reloaded.connected.value).toBe(true)
    mirror.stop()
  })

  it('does nothing on load for a tab that never opened one', async () => {
    const karaoke = await host()
    karaoke.resume()
    expect(open.size).toBe(0)
  })

  it('notices the window closing', async () => {
    const karaoke = await host()
    karaoke.open()
    const mirror = await stage(hostId())
    const sayBye = window.addEventListener.mock.calls.find(
      ([event]) => event === 'pagehide'
    )[1]
    sayBye()
    expect(karaoke.connected.value).toBe(false)
    mirror.stop()
  })

  it('notices the window going away silently', async () => {
    const karaoke = await host()
    karaoke.open()
    const mirror = await stage(hostId())
    mirror.stop()
    vi.advanceTimersByTime(STAGE_TIMEOUT_MS + 1)
    expect(karaoke.connected.value).toBe(false)
  })

  it('goes back to waiting when the main window disappears', async () => {
    const karaoke = await host()
    karaoke.open()
    const id = hostId()
    const mirror = await stage(id)
    expect(mirror.currentTrack.value).not.toBeNull()
    const channels = [...open.get(stageChannelName(id))]
    channels[0].close()
    vi.advanceTimersByTime(STAGE_TIMEOUT_MS + STAGE_PING_MS)
    expect(mirror.currentTrack.value).toBeNull()
    expect(mirror.isPlaying.value).toBe(false)
    mirror.stop()
  })
})
