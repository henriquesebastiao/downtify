import { describe, expect, it } from 'vitest'
import { shouldJumpToActive } from '../lib/queueTab.js'

describe('shouldJumpToActive', () => {
  it('jumps when downloads start from idle on another tab', () => {
    expect(shouldJumpToActive(1, 0, 'queued')).toBe(true)
    expect(shouldJumpToActive(2, undefined, 'all')).toBe(true)
  })

  it('stays put once something is already downloading', () => {
    // A finished item starts the next one: active goes 1 -> 2 while the
    // viewer is reading another tab. It must not pull them back.
    expect(shouldJumpToActive(2, 1, 'queued')).toBe(false)
    expect(shouldJumpToActive(1, 2, 'done')).toBe(false)
  })

  it('does nothing when already on the active tab', () => {
    expect(shouldJumpToActive(1, 0, 'active')).toBe(false)
  })

  it('does nothing when nothing is downloading', () => {
    expect(shouldJumpToActive(0, 0, 'queued')).toBe(false)
  })
})
