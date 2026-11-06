import { describe, expect, it, vi } from 'vitest'
import { readMixIndex } from '../model/musicAiRead'

describe('initial playlist read recovery', () => {
  it('recovers a temporary startup failure without generating a playlist', async () => {
    const fetch = vi.fn().mockRejectedValueOnce({ response: { status: 503 } }).mockResolvedValue(['synthetic-mix'])
    const sleep = vi.fn().mockResolvedValue()
    expect(await readMixIndex(fetch, () => true, sleep)).toEqual(['synthetic-mix'])
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(sleep).toHaveBeenCalledWith(1500)
  })
  it.each([401, 403, 404, 409, 429, 500])('does not retry HTTP %i', async status => {
    const failure = { response: { status } }, fetch = vi.fn().mockRejectedValue(failure)
    await expect(readMixIndex(fetch, () => true, vi.fn())).rejects.toBe(failure)
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('bounds requests and delay when the service remains unavailable', async () => {
    const failure = new Error('timeout'), fetch = vi.fn().mockRejectedValue(failure), sleep = vi.fn().mockResolvedValue()
    await expect(readMixIndex(fetch, () => true, sleep)).rejects.toBe(failure)
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(sleep.mock.calls).toEqual([[1500], [3000]])
  })
  it('does not request again after an account, module or view change', async () => {
    let current = true
    const fetch = vi.fn().mockRejectedValue(new Error('timeout'))
    expect(await readMixIndex(fetch, () => current, async () => { current = false })).toBeUndefined()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
