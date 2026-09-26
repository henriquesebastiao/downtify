import { describe, expect, it } from 'vitest'
import { QUEUE_ROW_GAP, queueRowEstimate } from '../lib/queueList.js'

describe('queueRowEstimate', () => {
  it('sizes compact queued/done rows as the cover tile plus gap', () => {
    expect(queueRowEstimate('queued')).toBe(56 + QUEUE_ROW_GAP)
    expect(queueRowEstimate('done')).toBe(56 + QUEUE_ROW_GAP)
  })

  it('gives active and failed rows extra room for progress / forms', () => {
    expect(queueRowEstimate('active')).toBeGreaterThan(
      queueRowEstimate('queued')
    )
    expect(queueRowEstimate('failed')).toBeGreaterThan(
      queueRowEstimate('active')
    )
  })
})
