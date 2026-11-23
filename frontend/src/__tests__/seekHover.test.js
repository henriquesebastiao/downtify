import { describe, expect, it } from 'vitest'
import { railRatio, tooltipLeft } from '../lib/seekHover.js'

describe('railRatio', () => {
  const rect = { left: 100, width: 400 }

  it('maps the pointer onto the rail', () => {
    expect(railRatio(100, rect)).toBe(0)
    expect(railRatio(300, rect)).toBe(0.5)
    expect(railRatio(500, rect)).toBe(1)
  })

  it('clamps past either end, so the wide hit area still seeks', () => {
    expect(railRatio(40, rect)).toBe(0)
    expect(railRatio(560, rect)).toBe(1)
  })

  it('is 0 for a rail that has no size yet', () => {
    expect(railRatio(300, { left: 0, width: 0 })).toBe(0)
    expect(railRatio(300, null)).toBe(0)
  })
})

describe('tooltipLeft', () => {
  it('centres the tooltip over the position', () => {
    expect(tooltipLeft(0.5, 400, 40)).toBe(180)
  })

  it('keeps the tooltip within the slack at the ends', () => {
    expect(tooltipLeft(0, 400, 40, 16)).toBe(-16)
    expect(tooltipLeft(1, 400, 40, 16)).toBe(376)
    expect(tooltipLeft(0, 400, 40, 0)).toBe(0)
    expect(tooltipLeft(1, 400, 40, 0)).toBe(360)
  })

  it('centres on the rail when the tooltip is wider than the room', () => {
    expect(tooltipLeft(0.9, 20, 60, 0)).toBe(-20)
  })
})
