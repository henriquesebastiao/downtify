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
