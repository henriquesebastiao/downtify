import { beforeEach, afterEach, expect, it, vi } from 'vitest'
const { resumeEqualizer } = vi.hoisted(() => ({ resumeEqualizer: vi.fn() }))
vi.mock('/src/model/equalizer', () => ({
  attachEqualizer() {},
  resumeEqualizer,
}))
vi.mock('/src/model/streamResolve', () => ({
  resolveTrackUrl: vi.fn(),
  warmServerCache: vi.fn(),
}))
let player, node, handlers
beforeEach(async () => {
  vi.resetModules()
  vi.useFakeTimers()
  handlers = {}
  globalThis.window = {
    innerWidth: 1280,
    addEventListener() {},
    location: { protocol: 'http:', hostname: 'localhost', port: '' },
  }
  globalThis.localStorage = {
    getItem: () => null,
    setItem() {},
    removeItem() {},
  }
  node = {
    src: '',
    currentTime: 0,
    duration: 120,
    buffered: { length: 0 },
    volume: 1,
    playbackRate: 1,
    play: vi.fn(async () => {}),
    pause: vi.fn(),
    load() {},
    removeAttribute() {
      this.src = ''
    },
    addEventListener(name, fn) {
      handlers[name] = fn
    },
  }
  globalThis.Audio = function () {
    return node
  }
  player = (await import('../model/player')).usePlayer()
  player.playList(['a.mp3', 'b.mp3', 'c.mp3'])
  node.currentTime = 42
  resumeEqualizer.mockClear()
})
afterEach(() => {
  player.detachDj()
  vi.useRealTimers()
})
function transport() {
  return {
    play: vi.fn(),
    pause: vi.fn(),
    next: vi.fn(),
    unload: vi.fn(),
    presentation: (position) => ({
      current: { file: 'dj.mp3', title: 'DJ' },
      next: { file: 'next.mp3' },
      elapsed: position,
      duration: 120,
    }),
  }
}
it('uses the same audio and transport while retaining the classic queue', () => {
  const dj = transport()
  expect(player.attachDj(dj)).toBe(node)
  expect(resumeEqualizer).toHaveBeenCalledOnce()
  expect(player.currentTrack.value.title).toBe('DJ')
  expect(player.upcoming.value.map((x) => x.track.file)).toEqual(['next.mp3'])
  player.play()
  player.next()
  player.pause()
  expect(resumeEqualizer).toHaveBeenCalledTimes(2)
  expect(dj.play).toHaveBeenCalledOnce()
  expect(dj.next).toHaveBeenCalledOnce()
  expect(dj.pause).toHaveBeenCalledOnce()
  player.detachDj()
  expect(dj.unload).toHaveBeenCalledOnce()
  expect(player.currentTrack.value.file).toBe('a.mp3')
  expect(player.currentTime.value).toBe(42)
  expect(player.playlist.value).toHaveLength(3)
})
it('routes the sleep timer to the DJ server and local audio', () => {
  const dj = transport()
  player.attachDj(dj)
  player.setSleepTimer(5)
  vi.advanceTimersByTime(300000)
  expect(dj.pause).toHaveBeenCalledOnce()
  expect(node.pause).toHaveBeenCalled()
  expect(player.sleepAt.value).toBeNull()
})
it('hands over at the actual end without advancing or restarting another song', () => {
  const handover = vi.fn(() => true)
  player.armDjHandover(handover)
  handlers.ended()
  expect(handover).toHaveBeenCalledOnce()
  expect(player.currentIndex.value).toBe(0)
})
it('clears an armed handover after an explicit selection change', () => {
  const handover = vi.fn(() => true)
  player.armDjHandover(handover)
  player.playAt(1)
  handlers.ended()
  expect(handover).not.toHaveBeenCalled()
  expect(player.currentIndex.value).toBe(2)
})
