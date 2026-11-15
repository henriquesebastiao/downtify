import { afterEach, beforeEach, expect, it, vi } from 'vitest'

vi.mock('/src/model/equalizer', () => ({
  attachEqualizer() {},
  resumeEqualizer() {},
}))
vi.mock('/src/model/streamResolve', () => ({
  resolveTrackUrl: vi.fn(),
  warmServerCache: vi.fn(),
}))
vi.mock('/src/model/ui', () => ({ useUi: () => ({ toast: vi.fn() }) }))
vi.mock('/src/model/musicAI', async () => {
  const { ref } = await import('vue')
  return {
    musicAI: {
      account: ref(1),
      capabilities: ref({
        dj_navigation: true,
        features: { dj_prepared: true, dj_interactive: true },
      }),
      refresh: vi.fn(async () => {}),
      djSession: vi.fn(),
      commandDj: vi.fn(async () => {}),
      stopDj: vi.fn(async () => {}),
      createDj: vi.fn(),
      cancelDjRequest: vi.fn(async () => {}),
      mediaUrl: (path) => path,
    },
  }
})
vi.mock('/src/model/djStream', () => ({
  createDjStream: ({ media }) => ({
    connect: vi.fn(async () => true),
    unload: vi.fn(),
    position: () => media.currentTime,
  }),
}))

let player, controller, music, node, handlers
const flush = async () => {
  for (let i = 0; i < 12; i++) await Promise.resolve()
}
const session = () => ({
  id: 'a'.repeat(32),
  mode: 'interactive',
  state: 'playing',
  queue_order: true,
  media_url: '/stream',
  tracks: [
    { id: 'a', file: 'a.mp3', title: 'A' },
    { id: 'b', file: 'b.mp3', title: 'B' },
  ],
  timeline: [
    { id: 'a', start: 0, end: 100, cue: 10, speed: 1 },
    { id: 'b', start: 90, end: 200, cue: 5, speed: 1.02 },
  ],
})
beforeEach(async () => {
  vi.resetModules()
  vi.useFakeTimers()
  handlers = new Map()
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
    paused: true,
    buffered: { length: 0 },
    volume: 1,
    playbackRate: 1,
    play: vi.fn(async () => {
      node.paused = false
      for (const f of handlers.get('play') || []) f()
    }),
    pause: vi.fn(() => {
      node.paused = true
      for (const f of handlers.get('pause') || []) f()
    }),
    load() {},
    removeAttribute() {
      this.src = ''
    },
    addEventListener(name, fn) {
      if (!handlers.has(name)) handlers.set(name, new Set())
      handlers.get(name).add(fn)
    },
    removeEventListener(name, fn) {
      handlers.get(name)?.delete(fn)
    },
  }
  globalThis.Audio = function () {
    return node
  }
  player = (await import('../model/player')).usePlayer()
  music = (await import('../model/musicAI')).musicAI
  controller = (await import('../model/djController')).djController
  music.djSession.mockResolvedValue(session())
  player.playList(['a.mp3', 'b.mp3', 'c.mp3'])
  node.play.mockClear()
})
afterEach(async () => {
  await controller.stop()
  player.stop()
  vi.clearAllTimers()
  vi.useRealTimers()
})

it('fences an old paused status after returning to the classic player', async () => {
  let resolve
  music.djSession.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      })
  )
  await controller.listen(session())
  await vi.advanceTimersByTimeAsync(5000)
  player.playAt(1)
  const pauses = node.pause.mock.calls.length
  resolve({ ...session(), state: 'paused' })
  await flush()
  expect(controller.session.value).toBeNull()
  expect(player.dj.value).toBeNull()
  expect(node.pause).toHaveBeenCalledTimes(pauses)
  expect(player.currentTrack.value.file).toBe('b.mp3')
})

it('keeps an interactive mix selected on a refused next', async () => {
  await controller.listen(session())
  player.pause()
  await flush()
  music.commandDj.mockRejectedValueOnce({
    response: { status: 409, data: { detail: 'Rendu terminé' } },
  })
  player.next()
  await flush()
  expect(controller.session.value.id).toBe(session().id)
  expect(player.dj.value).not.toBeNull()
  expect(node.paused).toBe(true)
  expect(controller.failure.value).toBe('Rendu terminé')
})

it('applies a confirmed next inside the stream without undoing a pause', async () => {
  await controller.listen(session())
  player.pause()
  await flush()
  node.currentTime = 20
  const plays = node.play.mock.calls.length
  music.commandDj.mockResolvedValueOnce({
    accepted: true,
    seek_to_seconds: 100,
  })
  player.next()
  await flush()
  expect(node.currentTime).toBe(100)
  expect(node.paused).toBe(true)
  expect(node.play).toHaveBeenCalledTimes(plays)
  expect(music.commandDj.mock.calls.at(-1)[1]).toMatchObject({
    action: 'next',
    payload: { position: '20' },
  })
})

it('discards a next response after returning to the classic selection', async () => {
  await controller.listen(session())
  let resolve
  music.commandDj.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      })
  )
  player.next()
  await flush()
  player.playAt(1)
  const position = node.currentTime
  resolve({ accepted: true, seek_to_seconds: 100 })
  await flush()
  expect(player.dj.value).toBeNull()
  expect(node.currentTime).toBe(position)
})

it('navigates prepared markers through the shared transport while paused', async () => {
  await controller.listen({ ...session(), mode: 'prepared', state: 'ready' })
  player.pause()
  await flush()
  music.commandDj.mockClear()
  player.next()
  await flush()
  expect(node.currentTime).toBe(100)
  player.prev()
  await flush()
  expect(node.currentTime).toBe(0)
  expect(node.paused).toBe(true)
  expect(music.commandDj).not.toHaveBeenCalled()
})

it('pauses immediately while a resume command is pending and never autoplays its late result', async () => {
  let resolve
  music.commandDj.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      })
  )
  const start = controller.listen(session())
  await flush()
  player.pause()
  expect(node.paused).toBe(true)
  resolve({ ok: true })
  await start
  await flush()
  expect(node.play).not.toHaveBeenCalled()
  expect(music.commandDj.mock.calls.map((args) => args[1].action)).toEqual([
    'resume',
    'pause',
  ])
})

it('does not turn a server render status into a pause or resume command', async () => {
  await controller.listen(session())
  const pauses = node.pause.mock.calls.length
  music.djSession.mockResolvedValue({ ...session(), state: 'paused' })
  await vi.advanceTimersByTimeAsync(5000)
  expect(node.pause).toHaveBeenCalledTimes(pauses)
  player.pause()
  const plays = node.play.mock.calls.length
  music.djSession.mockResolvedValue(session())
  await vi.advanceTimersByTimeAsync(5000)
  expect(node.play).toHaveBeenCalledTimes(plays)
})

it('cleans up 25 normal-DJ-normal cycles without retaining old observers or polling', async () => {
  const baseline = handlers.get('pause')?.size || 0
  for (let i = 0; i < 25; i++) {
    await controller.listen(session())
    player.pause()
    await controller.stop()
    player.playAt(0)
    expect(controller.session.value).toBeNull()
    expect(player.dj.value).toBeNull()
    expect(handlers.get('pause')?.size).toBe(baseline)
  }
  const calls = music.djSession.mock.calls.length
  await vi.advanceTimersByTimeAsync(10000)
  expect(music.djSession).toHaveBeenCalledTimes(calls)
})

it('returns to the dominant title and maps its tempo-adjusted source position', async () => {
  await controller.listen(session())
  node.currentTime = 97
  player.refreshDj(97)
  await controller.stop()
  expect(player.currentTrack.value.file).toBe('b.mp3')
  expect(player.currentTime.value).toBeCloseTo(5 + 7 * 1.02)
})

it('cancels an unknown server creation and rejects its late successful response', async () => {
  music.capabilities.value.dj = {
    interactive_ready: true,
    queue_supported: true,
  }
  let resolve
  music.createDj.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      })
  )
  const preparing = controller.startTheme('detente')
  await flush()
  const nonce = music.createDj.mock.calls[0][0].request_id
  await controller.stop()
  expect(music.cancelDjRequest).toHaveBeenCalledWith(nonce)
  resolve(session())
  await preparing
  expect(controller.session.value).toBeNull()
  expect(player.dj.value).toBeNull()
  expect(music.stopDj).toHaveBeenCalledWith(session().id)
})

it('does not open a summarized set after a manual selection supersedes its lookup', async () => {
  let resolve
  music.djSession.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      })
  )
  const opening = controller.listen({ ...session(), tracks: [] })
  player.playAt(2)
  resolve(session())
  await opening
  expect(player.dj.value).toBeNull()
  expect(player.currentTrack.value.file).toBe('c.mp3')
})

it('restores a new continuous deck and its next title after the initial pool has changed', async () => {
  await controller.listen(session())
  node.currentTime = 195
  music.djSession.mockResolvedValue({
    ...session(),
    continuous: true,
    queue_order: false,
    tracks: [
      { id: 'c', file: 'c.mp3', title: 'C' },
      { id: 'd', file: 'd.mp3', title: 'D' },
    ],
    timeline: [
      { id: 'c', start: 180, end: 280, cue: 5, speed: 1.01, occurrence: 24 },
      { id: 'd', start: 270, end: 380, cue: 0, speed: 1, occurrence: 25 },
    ],
  })
  await vi.advanceTimersByTimeAsync(5000)
  await controller.stop()
  expect(player.currentTrack.value.file).toBe('c.mp3')
  expect(player.currentTime.value).toBeCloseTo(20.15)
  expect(player.upcoming.value[0].track.file).toBe('d.mp3')
})

it('keeps a prepared server set reusable after returning to classic playback', async () => {
  await controller.listen({ ...session(), mode: 'prepared', state: 'ready' })
  await controller.stop()
  expect(player.dj.value).toBeNull()
  expect(music.stopDj).not.toHaveBeenCalled()
})

it('finishes the current seed and hands over without repeating it', async () => {
  music.capabilities.value = {
    features: { dj_interactive: true },
    dj_seed_mix: true,
    dj: { interactive_ready: true, queue_supported: true },
  }
  const value = {
    ...session(),
    state: 'paused',
    queue_order: false,
    tracks: [
      { id: 'b', file: 'b.mp3', title: 'B' },
      { id: 'c', file: 'c.mp3', title: 'C' },
    ],
    timeline: [
      { id: 'b', start: 0, end: 100 },
      { id: 'c', start: 90, end: 200 },
    ],
  }
  music.createDj.mockResolvedValue(value)
  music.djSession.mockResolvedValue(value)
  await controller.startSeed(player.currentTrack.value)
  expect(music.createDj.mock.calls[0][0]).toMatchObject({
    seed_file: 'a.mp3',
    skip_seed: true,
  })
  await vi.advanceTimersByTimeAsync(2000)
  expect(player.dj.value).toBeNull()
  expect(player.currentTrack.value.file).toBe('a.mp3')
  for (const fn of handlers.get('ended') || []) fn()
  await flush()
  expect(player.dj.value).not.toBeNull()
  expect(player.currentTrack.value.file).toBe('b.mp3')
})

it('cancels queue preparation as soon as classic playback advances naturally', async () => {
  music.capabilities.value.dj = {
    interactive_ready: true,
    queue_supported: true,
  }
  let resolve
  music.createDj.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done
      })
  )
  const preparing = controller.startQueue()
  await flush()
  const nonce = music.createDj.mock.calls[0][0].request_id
  for (const fn of handlers.get('ended') || []) fn()
  await flush()
  expect(music.cancelDjRequest).toHaveBeenCalledWith(nonce)
  resolve(session())
  await preparing
  expect(player.dj.value).toBeNull()
})
