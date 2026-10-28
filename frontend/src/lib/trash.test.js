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
