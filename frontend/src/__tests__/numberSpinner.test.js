import { describe, expect, it } from 'vitest'
import { clampSpinnerValue } from '../model/numberSpinner.js'

describe('clampSpinnerValue', () => {
  it('leaves an in-range integer untouched', () => {
    expect(clampSpinnerValue(5, 1, 10)).toBe(5)
  })

  it('clamps below the minimum', () => {
    expect(clampSpinnerValue(0, 1, 10)).toBe(1)
    expect(clampSpinnerValue(-5, 1, 10)).toBe(1)
  })

  it('clamps above the maximum', () => {
    expect(clampSpinnerValue(15, 1, 10)).toBe(10)
  })

  it('rounds a fractional value before clamping', () => {
    expect(clampSpinnerValue(5.6, 1, 10)).toBe(6)
    expect(clampSpinnerValue(5.4, 1, 10)).toBe(5)
  })

  it('respects custom bounds', () => {
    expect(clampSpinnerValue(50, 1, 100)).toBe(50)
    expect(clampSpinnerValue(0, 5, 20)).toBe(5)
  })
})
