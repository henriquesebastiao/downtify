import { describe, expect, it, vi } from 'vitest'
vi.mock('/src/model/api', () => ({ default: {} }))
import { safeNormalizationGain } from '/src/model/normalization'

describe('playback normalization', () => {
  const profile = (integrated_lufs, true_peak_dbtp, gain_db) => ({
    state: 'ready',
    algorithm_version: 1,
    integrated_lufs,
    true_peak_dbtp,
    gain_db,
  })
  it('limits amplification and preserves true peak headroom', () => {
    expect(safeNormalizationGain(profile(-40, -20, 30))).toBe(12)
    expect(safeNormalizationGain(profile(-40, -5, 12))).toBe(4)
    expect(safeNormalizationGain(profile(-8, -0.5, -10))).toBe(-10)
  })
  it('keeps original volume for absent, silent, invalid or unsupported data', () => {
    expect(safeNormalizationGain(null)).toBe(0)
    expect(safeNormalizationGain({ state: 'silent' })).toBe(0)
    expect(
      safeNormalizationGain({ ...profile(-30, -20, 12), algorithm_version: 2 })
    ).toBe(0)
    expect(safeNormalizationGain(profile(NaN, -20, 12))).toBe(0)
  })
})
