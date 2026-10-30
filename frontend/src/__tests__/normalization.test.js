import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
vi.mock('/src/model/api', () => ({ default: { getTrackLoudness: vi.fn() } }))
import API from '/src/model/api'
import {
  applyTrackNormalization,
  getTrackNormalization,
  normalizationEnabled,
  normalizationGain,
  normalizationLevel,
  safeNormalizationGain,
} from '/src/model/normalization'

describe('playback normalization', () => {
  afterEach(async () => {
    normalizationLevel.value = 'normal'
    normalizationEnabled.value = false
    applyTrackNormalization(null)
    await nextTick()
  })
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
  it('raises the target while retaining measured peak protection', () => {
    const loud = profile(-8, -0.5, -10)
    expect(safeNormalizationGain(loud, 'normal')).toBe(-10)
    expect(safeNormalizationGain(loud, 'louder')).toBe(-4)
    expect(safeNormalizationGain(loud, 'maximum')).toBe(-0.5)
    expect(safeNormalizationGain(loud, 'invalid')).toBe(-10)
    expect(safeNormalizationGain(loud, 'toString')).toBe(-10)
  })
  it.each(['normal', 'louder', 'maximum'])(
    'never boosts invalid profiles in %s',
    (level) => {
      expect(safeNormalizationGain(null, level)).toBe(0)
      expect(safeNormalizationGain(profile(NaN, -1, -8), level)).toBe(0)
      expect(
        safeNormalizationGain(
          { ...profile(-12, -1, -6), state: 'unanalysed' },
          level
        )
      ).toBe(0)
    }
  )
  it('keeps all levels monotonic, capped and below the peak ceiling', () => {
    for (const integrated of [-35, -25, -15, -8])
      for (const peak of [-20, -6, -1, 0])
        for (const gain of [-17, -8, 0, 12]) {
          const values = ['normal', 'louder', 'maximum'].map((level) =>
            safeNormalizationGain(profile(integrated, peak, gain), level)
          )
          expect(values[0]).toBeLessThanOrEqual(values[1])
          expect(values[1]).toBeLessThanOrEqual(values[2])
          for (const value of values) {
            expect(value).toBeLessThanOrEqual(12)
            expect(value).toBeLessThanOrEqual(-1 - peak)
          }
        }
  })
  it('updates the playing profile when the choice changes', async () => {
    applyTrackNormalization(profile(-8, -0.5, -10))
    normalizationLevel.value = 'louder'
    await nextTick()
    expect(normalizationGain.value).toBe(-4)
    normalizationLevel.value = 'maximum'
    await nextTick()
    expect(normalizationGain.value).toBe(-0.5)
  })
  it('does not replace the playing profile with a prefetched profile', async () => {
    normalizationEnabled.value = true
    applyTrackNormalization(profile(-8, -0.5, -10))
    API.getTrackLoudness.mockResolvedValue({ data: profile(-35, -20, 12) })
    await getTrackNormalization({ file: 'prefetched-level-test.flac' })
    normalizationLevel.value = 'louder'
    await nextTick()
    expect(normalizationGain.value).toBe(-4)
    expect(API.getTrackLoudness).toHaveBeenCalledTimes(1)
  })
})
