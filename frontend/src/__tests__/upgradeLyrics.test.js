import { describe, expect, it } from 'vitest'
import { normalizeStatus } from '/src/lib/upgrade'

describe('upgrade lyrics outcome', () => {
  it('reads how the lyrics part of a run went', () => {
    const status = normalizeStatus({
      lyrics: { added: 3, not_found: 2, failed: 1, pending: 0 },
    })
    expect(status.lyrics).toEqual({
      added: 3,
      notFound: 2,
      failed: 1,
      pending: 0,
    })
  })

  it('is all zero before any run', () => {
    expect(normalizeStatus({}).lyrics).toEqual({
      added: 0,
      notFound: 0,
      failed: 0,
      pending: 0,
    })
  })
})
