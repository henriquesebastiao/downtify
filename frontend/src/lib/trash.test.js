import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ trashCapabilities: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: api }))

describe('trash feature negotiation', () => {
  beforeEach(() => {
    vi.resetModules()
    api.trashCapabilities.mockReset()
  })

  it('keeps trash disabled on servers without the opt-in capability', async () => {
    api.trashCapabilities.mockResolvedValue({
      data: { enabled: false, can_manage: false },
    })
    const { useTrashCapability } = await import('./trash')
    const capability = useTrashCapability()
    await capability.refresh()
    expect(capability.enabled.value).toBe(false)
    expect(capability.canManage.value).toBe(false)
  })

  it('allows the opted-in administrator UI', async () => {
    api.trashCapabilities.mockResolvedValue({
      data: { enabled: true, can_manage: true },
    })
    const { useTrashCapability } = await import('./trash')
    const capability = useTrashCapability()
    await capability.refresh()
    expect(capability.enabled.value).toBe(true)
    expect(capability.canManage.value).toBe(true)
  })

  it('handles an older or unavailable endpoint without an unhandled rejection', async () => {
    api.trashCapabilities.mockRejectedValue(new Error('not available'))
    const { useTrashCapability } = await import('./trash')
    const capability = useTrashCapability()
    await capability.refresh()
    expect(capability.enabled.value).toBe(false)
    expect(capability.canManage.value).toBe(false)
  })
})

describe('trash helpers', () => {
  it('maps unknown error codes to the generic message', async () => {
    const { trashErrorKey } = await import('./trash')
    expect(trashErrorKey('restore_collision')).toBe(
      'trash.errors.restore_collision'
    )
    expect(trashErrorKey('something_new')).toBe('trash.errors.unavailable')
    expect(trashErrorKey(undefined)).toBe('trash.errors.unavailable')
  })

  it('restores only kept, waiting or stopped songs within their retention', async () => {
    const { restorable } = await import('./trash')
    const now = 1_000_000_000_000
    expect(
      restorable({ state: 'trashed', expires_at: now / 1000 + 60 }, now)
    ).toBe(true)
    expect(
      restorable({ state: 'trashed', expires_at: now / 1000 - 1 }, now)
    ).toBe(false)
    expect(restorable({ state: 'pending', expires_at: null }, now)).toBe(true)
    expect(restorable({ state: 'error', expires_at: null }, now)).toBe(true)
    expect(restorable({ state: 'moving' }, now)).toBe(false)
    expect(restorable({ state: 'purged' }, now)).toBe(false)
  })

  it('lists at most a few files in the confirmation', async () => {
    const { previewLines } = await import('./trash')
    const items = Array.from({ length: 10 }, (_, i) => ({
      file: `Artist/Song ${i}.flac`,
      metadata: i ? { title: `Song ${i}`, artist: 'Artist' } : {},
    }))
    const { lines, more } = previewLines(items, 3)
    expect(lines).toEqual([
      '• Artist/Song 0.flac (FLAC)',
      '• Artist — Song 1 (FLAC)',
      '• Artist — Song 2 (FLAC)',
    ])
    expect(more).toBe(7)
  })
})
