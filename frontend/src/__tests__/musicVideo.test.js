import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { DRIFT_LIMIT, videoSyncAction } from '../lib/musicVideo'

const api = vi.hoisted(() => ({ getMusicVideo: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: api }))

describe('videoSyncAction', () => {
  it('leaves a video in step alone', () => {
    expect(
      videoSyncAction({
        audioTime: 10,
        videoTime: 10.1,
        duration: 200,
        playing: true,
        videoPaused: false,
      })
    ).toEqual({ seek: null, play: false, pause: false })
  })

  it('jumps to the song once it drifts', () => {
    const action = videoSyncAction({
      audioTime: 42,
      videoTime: 42 - DRIFT_LIMIT - 0.1,
      duration: 200,
      playing: true,
      videoPaused: false,
    })
    expect(action.seek).toBe(42)
  })

  it('plays and pauses with the song', () => {
    expect(
      videoSyncAction({
        audioTime: 1,
        videoTime: 1,
        duration: 9,
        playing: true,
      }).play
    ).toBe(true)
    expect(
      videoSyncAction({
        audioTime: 1,
        videoTime: 1,
        duration: 9,
        playing: false,
        videoPaused: false,
      }).pause
    ).toBe(true)
  })

  it('holds the last frame past the end of a shorter video', () => {
    expect(
      videoSyncAction({
        audioTime: 230,
        videoTime: 199.9,
        duration: 200,
        playing: true,
        videoPaused: false,
      })
    ).toEqual({ seek: null, play: false, pause: true })
  })
})

describe('useMusicVideo', () => {
  let model
  beforeEach(async () => {
    vi.resetModules()
    api.getMusicVideo.mockReset()
    model = await import('../model/musicVideo')
  })

  async function settle() {
    for (let i = 0; i < 4; i += 1) await nextTick()
  }

  it('finds the playing song’s video once, and only while wanted', async () => {
    api.getMusicVideo.mockResolvedValue({ data: { url: '/v?file=a.mp3' } })
    const track = ref({ file: 'a.mp3' })
    const on = ref(true)
    const url = model.useMusicVideo(track, () => on.value)
    await settle()
    expect(url.value).toBe('/v?file=a.mp3')

    on.value = false
    await settle()
    expect(url.value).toBe('')

    on.value = true
    await settle()
    expect(url.value).toBe('/v?file=a.mp3')
    expect(api.getMusicVideo).toHaveBeenCalledTimes(1)
  })

  it('has none for streams, podcasts and songs without one', async () => {
    api.getMusicVideo.mockRejectedValue({ response: { status: 404 } })
    const track = ref({ file: 'b.mp3' })
    const url = model.useMusicVideo(track, () => true)
    await settle()
    expect(url.value).toBe('')
    track.value = { file: 'c.mp3', stream: true }
    await settle()
    expect(url.value).toBe('')
    expect(api.getMusicVideo).toHaveBeenCalledTimes(1)
  })

  it('asks again once a "no video" answer is old (the video came later)', async () => {
    api.getMusicVideo
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValueOnce({ data: { url: '/v?file=d.mp3' } })
    expect(await model.musicVideoURL('d.mp3', 0)).toBe('')
    expect(await model.musicVideoURL('d.mp3', 1000)).toBe('')
    expect(api.getMusicVideo).toHaveBeenCalledTimes(1)
    expect(await model.musicVideoURL('d.mp3', model.MISS_TTL_MS + 1)).toBe(
      '/v?file=d.mp3'
    )
    // A video found is kept.
    expect(await model.musicVideoURL('d.mp3', 10 ** 9)).toBe('/v?file=d.mp3')
    expect(api.getMusicVideo).toHaveBeenCalledTimes(2)
  })

  it('finds a video that arrives while its song plays', async () => {
    vi.useFakeTimers()
    try {
      api.getMusicVideo
        .mockRejectedValueOnce({ response: { status: 404 } })
        .mockResolvedValueOnce({ data: { url: '/v?file=e.mp3' } })
      const url = model.useMusicVideo(ref({ file: 'e.mp3' }), () => true)
      await settle()
      expect(url.value).toBe('')
      await vi.advanceTimersByTimeAsync(model.MISS_TTL_MS + 100)
      await settle()
      expect(url.value).toBe('/v?file=e.mp3')
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('coverPicture', () => {
  const pillarboxed = {
    width: 480,
    height: 360,
    x: 80,
    y: 0,
    video_width: 640,
    video_height: 360,
  }

  it('zooms burnt-in bars out of a wide view', async () => {
    const { coverPicture } = await import('../lib/musicVideo')
    const box = coverPicture(pillarboxed, 1600, 900)
    // The picture (480 px wide) now spans the whole 1600 px view.
    const scale = box.width / 640
    expect(480 * scale).toBeGreaterThanOrEqual(1600 - 0.01)
    expect(box.left + 80 * scale).toBeLessThanOrEqual(0.01)
    expect(box.left + (80 + 480) * scale).toBeGreaterThanOrEqual(1600 - 0.01)
    expect(box.top).toBeLessThanOrEqual(0)
    expect(box.top + 360 * scale).toBeGreaterThanOrEqual(900)
  })

  it('covers a tall phone view too', async () => {
    const { coverPicture } = await import('../lib/musicVideo')
    const box = coverPicture(pillarboxed, 390, 844)
    const scale = box.width / 640
    expect(360 * scale).toBeGreaterThanOrEqual(844 - 0.01)
    expect(box.left + 80 * scale).toBeLessThanOrEqual(0.01)
  })

  it('leaves a video without bars to object-fit: cover', async () => {
    const { coverPicture } = await import('../lib/musicVideo')
    expect(coverPicture(null, 1600, 900)).toBeNull()
    expect(coverPicture(pillarboxed, 0, 0)).toBeNull()
  })
})
