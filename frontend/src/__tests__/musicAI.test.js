import { beforeEach, describe, expect, it, vi } from 'vitest'

const { http } = vi.hoisted(() => ({ http: { get: vi.fn(), post: vi.fn(), defaults: { baseURL: 'http://localhost:8000' } } }))
vi.mock('axios', () => ({ default: { create: () => http } }))
vi.mock('/src/config', () => ({ default: { PROTOCOL: 'http:', BACKEND: 'localhost', PORT: 8000, BASEURL: '' } }))

describe('music AI capability isolation', () => {
  beforeEach(() => {
    vi.resetModules()
    http.get.mockReset()
    http.post.mockReset()
  })

  it('loads the new account after an older request finishes', async () => {
    const { musicAI } = await import('../model/musicAI')
    let resolveCaps, resolvePrefs
    http.get.mockImplementationOnce(() => new Promise((resolve) => { resolveCaps = resolve }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolvePrefs = resolve }))
      .mockResolvedValueOnce({ data: { owner: 2 } })
      .mockResolvedValueOnce({ data: { preferences: { daily: false } } })
    musicAI.setAccount(1)
    const first = musicAI.refresh()
    musicAI.setAccount(2)
    const second = musicAI.refresh()
    resolveCaps({ data: { owner: 1 } })
    resolvePrefs({ data: { preferences: { daily: true } } })
    await Promise.all([first, second])
    expect(http.get).toHaveBeenCalledTimes(4)
    expect(musicAI.capabilities.value.owner).toBe(2)
    expect(musicAI.preferences.value.daily).toBe(false)
  })

  it('backs off unavailable capabilities instead of querying on every playback event', async () => {
    const { musicAI } = await import('../model/musicAI')
    http.get.mockRejectedValue(new Error('offline'))
    musicAI.setAccount(1)
    await musicAI.refresh()
    await musicAI.refresh()
    expect(http.get).toHaveBeenCalledTimes(2)
    expect(musicAI.capabilities.value).toBeNull()
    await musicAI.refresh(true)
    expect(http.get).toHaveBeenCalledTimes(4)
  })

  it('accepts only local prepared and HLS entrypoints without credentials or arbitrary resource paths', async () => {
    const { musicAI } = await import('../model/musicAI')
    const root = `/api/v1/music-ai/dj/sessions/${'a'.repeat(32)}`
    expect(musicAI.mediaUrl(`${root}/media`)).toBe(`http://localhost:8000${root}/media`)
    expect(musicAI.mediaUrl(`${root}/hls/index.m3u8`)).toBe(`http://localhost:8000${root}/hls/index.m3u8`)
    for (const path of ['https://untrusted.test/music', `${root}/hls/../../private`,
      `${root}/media?token=caller`, `${root}/hls/key.bin`]) expect(() => musicAI.mediaUrl(path)).toThrow()
  })

  it('keeps normal creation and administrative continuity validation on distinct endpoints', async () => {
    const { musicAI } = await import('../model/musicAI')
    http.post.mockResolvedValue({ data: {} })
    const intent = { request_id: 'same-intent', mode: 'interactive', theme: 'fete', count: 40 }
    await musicAI.createDj(intent)
    await musicAI.validateDj(intent)
    expect(http.post.mock.calls[0]).toEqual(['/api/v1/music-ai/dj/sessions', intent])
    expect(http.post.mock.calls[1]).toEqual(['/api/v1/music-ai/dj/admin/validation-sessions', intent])
  })

  it('keeps only musical ids in a DJ selection and clears it when the account changes', async () => {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    musicAI.selectForDj([{ id: 'one', title: 'One', artist: 'A', file: '/private/path' }])
    expect(musicAI.djSelection.value).toEqual([{ id: 'one', title: 'One', artist: 'A' }])
    musicAI.setAccount(2)
    expect(musicAI.djSelection.value).toEqual([])
  })
})
