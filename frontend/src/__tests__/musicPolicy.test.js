import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ getServerInfo: vi.fn(), onMessage: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: api }))

import {
  libraryOnly,
  refreshMusicPolicy,
  startMusicPolicy,
} from '../model/musicPolicy'

describe('server library-only policy', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    libraryOnly.value = false
    api.onMessage.mockReturnValue(vi.fn())
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('reads the policy and keeps it when the server is unreachable', async () => {
    api.getServerInfo.mockResolvedValueOnce({ data: { library_only: true } })
    await refreshMusicPolicy()
    expect(libraryOnly.value).toBe(true)
    api.getServerInfo.mockRejectedValueOnce(new Error('unreachable'))
    await refreshMusicPolicy()
    expect(libraryOnly.value).toBe(true)
  })

  it('supports servers that predate the setting', async () => {
    libraryOnly.value = true
    api.getServerInfo.mockResolvedValueOnce({ data: { version: '3.7.0' } })
    await refreshMusicPolicy()
    expect(libraryOnly.value).toBe(false)
  })

  it('applies live changes and unregisters on shutdown', async () => {
    api.getServerInfo.mockResolvedValue({ data: { library_only: false } })
    const unsubscribe = vi.fn()
    api.onMessage.mockReturnValue(unsubscribe)
    const stop = startMusicPolicy()
    await Promise.resolve()
    const listener = api.onMessage.mock.calls[0][0]
    listener({ type: 'music_policy_changed', library_only: true })
    expect(libraryOnly.value).toBe(true)
    listener({ type: 'music_policy_changed', library_only: false })
    expect(libraryOnly.value).toBe(false)
    stop()
    expect(unsubscribe).toHaveBeenCalledOnce()
    expect(vi.getTimerCount()).toBe(0)
  })
})
