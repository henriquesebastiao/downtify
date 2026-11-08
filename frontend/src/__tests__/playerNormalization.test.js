import { beforeEach, describe, expect, it, vi } from 'vitest'
const api = vi.hoisted(() => ({ getTrackLoudness: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: api }))
vi.mock('/src/model/streamResolve', () => ({
  resolveTrackUrl: vi.fn(),
  warmServerCache: vi.fn(),
}))

describe('normalization before playback', () => {
  let player, normalization, audio
  const track = (name) => ({
    file: `${name}.mp3`,
    url: `/downloads/${name}.mp3`,
  })
  beforeEach(async () => {
    vi.resetModules()
    api.getTrackLoudness.mockReset()
    globalThis.localStorage = {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    }
    globalThis.window = { innerWidth: 1280, addEventListener: () => {} }
    audio = {
      src: '',
      currentTime: 0,
      addEventListener: () => {},
      play: vi.fn(async () => {}),
      pause: vi.fn(),
      removeAttribute: () => {},
    }
    globalThis.Audio = function () {
      return audio
    }
    normalization = await import('../model/normalization')
    normalization.normalizationEnabled.value = true
    player = (await import('../model/player')).usePlayer()
  })
  it('applies the measured gain before the first play', async () => {
    let finish
    api.getTrackLoudness.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    player.playList([track('one')])
    expect(audio.play).not.toHaveBeenCalled()
    finish({
      data: {
        state: 'ready',
        algorithm_version: 1,
        integrated_lufs: -8,
        true_peak_dbtp: -1,
        gain_db: -10,
      },
    })
    await vi.waitFor(() => expect(audio.play).toHaveBeenCalledTimes(1))
    expect(normalization.normalizationGain.value).toBe(-10)
  })
  it('never restarts playback when paused while awaiting a measurement', async () => {
    let finish
    api.getTrackLoudness.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    player.playList([track('one')])
    player.pause()
    finish({ data: { state: 'unanalysed' } })
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(audio.play).not.toHaveBeenCalled()
  })
  it('falls back to original volume if the server is unavailable', async () => {
    api.getTrackLoudness.mockRejectedValue(new Error('offline'))
    player.playList([track('one')])
    await vi.waitFor(() => expect(audio.play).toHaveBeenCalledTimes(1))
    expect(normalization.normalizationGain.value).toBe(0)
  })
})

describe('normalization profiles already known', () => {
  let player, normalization, audio
  const track = (name) => ({
    file: `${name}.mp3`,
    url: `/downloads/${name}.mp3`,
  })
  const ready = (gain) => ({
    data: {
      state: 'ready',
      algorithm_version: 1,
      integrated_lufs: -18 - gain,
      true_peak_dbtp: -20,
      gain_db: gain,
    },
  })
  beforeEach(async () => {
    vi.resetModules()
    api.getTrackLoudness.mockReset()
    globalThis.localStorage = {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    }
    globalThis.window = { innerWidth: 1280, addEventListener: () => {} }
    audio = {
      src: '',
      currentTime: 0,
      paused: true,
      addEventListener: () => {},
      play: vi.fn(async () => {}),
      pause: vi.fn(),
      removeAttribute: () => {},
    }
    globalThis.Audio = function () {
      return audio
    }
    normalization = await import('../model/normalization')
    normalization.normalizationEnabled.value = true
    player = (await import('../model/player')).usePlayer()
  })
  it('resumes a paused song at once, without asking again', async () => {
    api.getTrackLoudness.mockResolvedValue(ready(-6))
    player.playList([track('one')])
    await vi.waitFor(() => expect(audio.play).toHaveBeenCalledTimes(1))
    player.pause()
    player.play()
    expect(audio.play).toHaveBeenCalledTimes(2)
    expect(api.getTrackLoudness).toHaveBeenCalledTimes(1)
    expect(normalization.normalizationGain.value).toBe(-6)
  })
  it('looks up the next song while this one plays', async () => {
    api.getTrackLoudness.mockImplementation(async (file) =>
      file === 'one.mp3' ? ready(-6) : ready(3)
    )
    player.playList([track('one'), track('two')])
    await vi.waitFor(() =>
      expect(api.getTrackLoudness).toHaveBeenCalledWith('two.mp3')
    )
    await vi.waitFor(() => expect(audio.play).toHaveBeenCalledTimes(1))
    await new Promise((resolve) => setTimeout(resolve, 0))
    player.next()
    // Known already: starts without waiting on the server.
    expect(audio.play).toHaveBeenCalledTimes(2)
    expect(normalization.normalizationGain.value).toBe(3)
    expect(api.getTrackLoudness).toHaveBeenCalledTimes(2)
  })
  it('levels the playing song when switched on mid-song', async () => {
    normalization.normalizationEnabled.value = false
    await new Promise((resolve) => setTimeout(resolve, 0))
    player.playList([track('one')])
    expect(audio.play).toHaveBeenCalledTimes(1)
    expect(api.getTrackLoudness).not.toHaveBeenCalled()
    api.getTrackLoudness.mockResolvedValue(ready(-4))
    normalization.normalizationEnabled.value = true
    await vi.waitFor(() =>
      expect(normalization.normalizationGain.value).toBe(-4)
    )
    expect(audio.play).toHaveBeenCalledTimes(1)
  })
  it('asks again after a failed lookup', async () => {
    api.getTrackLoudness.mockRejectedValueOnce(new Error('offline'))
    player.playList([track('one')])
    await vi.waitFor(() => expect(audio.play).toHaveBeenCalledTimes(1))
    api.getTrackLoudness.mockResolvedValue(ready(-2))
    player.playAt(0)
    await vi.waitFor(() => expect(audio.play).toHaveBeenCalledTimes(2))
    expect(normalization.normalizationGain.value).toBe(-2)
  })
})
