import { beforeEach, describe, expect, it, vi } from 'vitest'

const { http } = vi.hoisted(() => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000' },
  },
}))
vi.mock('axios', () => ({ default: { create: () => http } }))
vi.mock('/src/config', () => ({
  default: { PROTOCOL: 'http:', BACKEND: 'localhost', PORT: 8000, BASEURL: '' },
}))

describe('music AI capability isolation', () => {
  beforeEach(() => {
    vi.resetModules()
    http.get.mockReset()
    http.post.mockReset()
  })

  it('loads the new account after an older request finishes', async () => {
    const { musicAI } = await import('../model/musicAI')
    let resolveCaps, resolvePrefs
    http.get
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveCaps = resolve
          })
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolvePrefs = resolve
          })
      )
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
    expect(musicAI.mediaUrl(`${root}/media`)).toBe(
      `http://localhost:8000${root}/media`
    )
    expect(musicAI.mediaUrl(`${root}/hls/index.m3u8`)).toBe(
      `http://localhost:8000${root}/hls/index.m3u8`
    )
    for (const path of [
      'https://untrusted.test/music',
      `${root}/hls/../../private`,
      `${root}/media?token=caller`,
      `${root}/hls/key.bin`,
    ])
      expect(() => musicAI.mediaUrl(path)).toThrow()
  })

  it('keeps normal creation and administrative continuity validation on distinct endpoints', async () => {
    const { musicAI } = await import('../model/musicAI')
    http.post.mockResolvedValue({ data: {} })
    const intent = {
      request_id: 'same-intent',
      mode: 'interactive',
      theme: 'fete',
      count: 40,
    }
    await musicAI.createDj(intent)
    await musicAI.validateDj(intent)
    expect(http.post.mock.calls[0]).toEqual([
      '/api/v1/music-ai/dj/sessions',
      intent,
      {},
    ])
    expect(http.post.mock.calls[1]).toEqual([
      '/api/v1/music-ai/dj/admin/validation-sessions',
      intent,
    ])
  })

  it('keeps only musical ids in a DJ selection and clears it when the account changes', async () => {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    musicAI.selectForDj([
      { id: 'one', title: 'One', artist: 'A', file: '/private/path' },
    ])
    expect(musicAI.djSelection.value).toEqual([
      { id: 'one', title: 'One', artist: 'A' },
    ])
    musicAI.setAccount(2)
    expect(musicAI.djSelection.value).toEqual([])
  })

  it('renews explicitly with an owner-free idempotent request and drops the home cache', async () => {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    musicAI.capabilities.value = { playlist_refresh: true }
    http.get.mockResolvedValueOnce({ data: { cards: [{ mood: 'rock' }] } })
    await musicAI.home()
    http.post.mockResolvedValueOnce({ data: { accepted: true, revision: 1 } })
    await musicAI.renewPlaylists('same-request')
    expect(http.post).toHaveBeenCalledWith(
      '/api/v1/music-ai/playlists/refresh',
      {
        request_id: 'same-request',
      }
    )
    http.get.mockResolvedValueOnce({ data: { cards: [] } })
    expect(await musicAI.home()).toEqual([])
    expect(http.get).toHaveBeenCalledTimes(2)
  })

  it('rejects an old account renewal response without clearing the new home cache', async () => {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    musicAI.capabilities.value = { playlist_refresh: true }
    let finish
    http.post.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    const renewal = musicAI.renewPlaylists('old')
    musicAI.setAccount(2)
    http.get.mockResolvedValueOnce({ data: { cards: [{ mood: 'pop' }] } })
    await musicAI.home()
    finish({ data: { accepted: true } })
    await expect(renewal).rejects.toThrow('Le compte a changé')
    expect(await musicAI.home()).toEqual([{ mood: 'pop' }])
    expect(http.get).toHaveBeenCalledTimes(1)
  })

  it('does not call the renewal endpoint on an older server', async () => {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    await expect(musicAI.renewPlaylists('intent')).rejects.toThrow()
    expect(http.post).not.toHaveBeenCalled()
  })
})

describe('weekly audio sets', () => {
  beforeEach(() => {
    vi.resetModules()
    http.get.mockReset()
    http.post.mockReset()
  })
  async function supported() {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    musicAI.capabilities.value = {
      version: 1,
      dj_weekly_sets: true,
      dj_asset_copies: true,
      dj_asset_consumers: true,
      features: { weekly: true, dj_prepared: true, dj_weekly: true },
    }
    return musicAI
  }
  it('is off on legacy servers and sends no request', async () => {
    const { musicAI } = await import('../model/musicAI')
    musicAI.setAccount(1)
    expect(musicAI.weeklySetsEnabled()).toBeFalsy()
    expect(await musicAI.weeklySets()).toBeNull()
    await expect(musicAI.prepareWeekly('rock', 'nonce')).rejects.toThrow()
    expect(http.get).not.toHaveBeenCalled()
    expect(http.post).not.toHaveBeenCalled()
  })
  it('keeps weekly reading separate from explicit copy and preparation intents', async () => {
    const musicAI = await supported()
    http.get.mockResolvedValue({ data: { cards: [], copies: [] } })
    await musicAI.weeklySets()
    expect(http.post).not.toHaveBeenCalled()
    http.post.mockResolvedValue({ data: { id: 'a'.repeat(32) } })
    await musicAI.copyDj('a'.repeat(32), 'Mon rock', 'same-copy')
    expect(http.post).toHaveBeenLastCalledWith(
      `/api/v1/music-ai/dj/sessions/${'a'.repeat(32)}/copies`,
      { request_id: 'same-copy', name: 'Mon rock' }
    )
    await musicAI.prepareWeekly('rock', 'same-prepare')
    expect(http.post).toHaveBeenLastCalledWith(
      '/api/v1/music-ai/dj/weekly/rock',
      { request_id: 'same-prepare' }
    )
  })
  it('fences a weekly response after an account change', async () => {
    const musicAI = await supported()
    let resolve
    http.get.mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        })
    )
    const pending = musicAI.weeklySets()
    musicAI.setAccount(2)
    resolve({ data: { cards: [{ theme: 'private' }] } })
    expect(await pending).toBeNull()
  })
  it('uses a per-tab consumer only for compatible prepared media', async () => {
    const musicAI = await supported()
    const root = `/api/v1/music-ai/dj/sessions/${'a'.repeat(32)}`
    const media = new URL(musicAI.mediaUrl(`${root}/media`))
    expect(media.searchParams.get('consumer')).toMatch(/^[a-f0-9-]{36}$/)
    expect(musicAI.mediaUrl(`${root}/hls/index.m3u8`)).not.toContain('?')
    expect(() => musicAI.mediaUrl(`${root}/media?consumer=caller`)).toThrow()
  })
})
