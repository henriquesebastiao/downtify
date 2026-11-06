import { describe, it, expect, vi } from 'vitest'
import { createDjStream } from '../model/djStream'

function fixture(supported = true) {
  const calls = { created: vi.fn(), attach: vi.fn(), load: vi.fn(), destroy: vi.fn(), handlers: new Map() }
  class Hls {
    static Events = { ERROR: 'error', FRAG_LOADED: 'fragment', LEVEL_LOADED: 'playlist' }
    static isSupported() { return supported }
    constructor() { calls.created() }
    on(event, callback) { calls.handlers.set(event, callback) }
    attachMedia(media) { calls.attach(media) }
    loadSource(url) { calls.load(url) }
    destroy() { calls.destroy() }
  }
  const media = { canPlayType: vi.fn(() => 'probably'), src: '' }
  const loadHls = vi.fn(async () => ({ default: Hls }))
  const options = { media, url: '/local/stream.m3u8', current: () => true, onFatal: vi.fn(), loadHls }
  return { calls, Hls, media, loadHls, options }
}

describe('DJ stream lifecycle', () => {
  it('maps a late HLS join to the absolute mix position using program dates', async () => {
    const f = fixture()
    f.Hls.prototype.playingDate = new Date('2026-11-06T14:02:00Z')
    const stream = createDjStream(f.options)
    await stream.connect()
    expect(stream.position(Date.parse('2026-11-06T14:00:00Z') / 1000)).toBe(120)
    stream.unload()
    delete f.Hls.prototype.playingDate
  })
  it('maps native HLS dates and retains a finite fallback on older streams', async () => {
    const f = fixture(false)
    f.media.currentTime = 12
    f.media.getStartDate = () => new Date('2026-11-06T14:01:00Z')
    const stream = createDjStream(f.options)
    await stream.connect()
    expect(stream.position(Date.parse('2026-11-06T14:00:00Z') / 1000)).toBe(72)
    expect(stream.position(null)).toBe(12)
  })
  it('opens no idle stream and coalesces concurrent play requests', async () => {
    const f = fixture()
    const stream = createDjStream(f.options)
    expect(f.loadHls).not.toHaveBeenCalled()
    expect(f.media.src).toBe('')
    expect(await Promise.all([stream.connect(), stream.connect()])).toEqual([true, true])
    await stream.connect()
    expect(f.calls.created).toHaveBeenCalledTimes(1)
    expect(f.calls.attach).toHaveBeenCalledWith(f.media)
    expect(f.calls.load).toHaveBeenCalledTimes(1)
    stream.unload()
    expect(f.calls.destroy).toHaveBeenCalledTimes(1)
  })

  it('keeps the native HLS fallback lazy too', async () => {
    const f = fixture(false)
    const stream = createDjStream(f.options)
    expect(f.media.src).toBe('')
    expect(await stream.connect()).toBe(true)
    expect(f.media.src).toBe('/local/stream.m3u8')
    expect(f.calls.created).not.toHaveBeenCalled()
  })

  it.each(['unload', 'owner'])('cannot attach after %s during module loading', async (action) => {
    const f = fixture()
    let resolve, allowed = true
    f.options.loadHls = () => new Promise(r => { resolve = r })
    f.options.current = () => allowed
    const stream = createDjStream(f.options)
    const pending = stream.connect()
    if (action === 'unload') stream.unload()
    else allowed = false
    resolve({ default: f.Hls })
    expect(await pending).toBe(false)
    expect(f.calls.created).not.toHaveBeenCalled()
    expect(f.media.src).toBe('')
  })

  it('refuses unsupported playback without opening a source', async () => {
    const f = fixture(false)
    f.media.canPlayType = () => ''
    const stream = createDjStream(f.options)
    await expect(stream.connect()).rejects.toThrow('unsupported-hls')
    expect(f.media.src).toBe('')
  })

  it('does not resume an existing stream after the account changes', async () => {
    const f = fixture()
    let allowed = true
    f.options.current = () => allowed
    const stream = createDjStream(f.options)
    expect(await stream.connect()).toBe(true)
    allowed = false
    expect(await stream.connect()).toBe(false)
    expect(f.calls.created).toHaveBeenCalledTimes(1)
  })

  it('exports aggregate transport measurements without request URLs or raw errors', async () => {
    const f = fixture()
    const onDiagnostic = vi.fn()
    const stream = createDjStream({ ...f.options, onDiagnostic })
    await stream.connect()
    f.calls.handlers.get('error')(null, { type: 'networkError', details: 'fragLoadTimeOut',
      fatal: false, response: { code: 503, url: '/private-secret' }, error: new Error('private-secret') })
    const value = onDiagnostic.mock.calls[0][0]
    expect(value.error).toMatchObject({ type: 'networkError', detail: 'fragLoadTimeOut', http_status: 503 })
    expect(JSON.stringify(value)).not.toContain('private-secret')
    stream.unload()
    f.calls.handlers.get('error')(null, { type: 'networkError' })
    expect(onDiagnostic).toHaveBeenCalledTimes(1)
  })

  it('destroys a fatal instance once and permits an explicit retry', async () => {
    const f = fixture()
    const stream = createDjStream(f.options)
    await stream.connect()
    const failedInstance = f.calls.handlers.get('error')
    failedInstance(null, { type: 'mediaError', fatal: true })
    failedInstance(null, { type: 'mediaError', fatal: true })
    expect(f.calls.destroy).toHaveBeenCalledTimes(1)
    expect(f.options.onFatal).toHaveBeenCalledTimes(1)
    expect(await stream.connect()).toBe(true)
    expect(f.calls.created).toHaveBeenCalledTimes(2)
  })
})
