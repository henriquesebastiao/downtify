import { describe, expect, it } from 'vitest'
import { WAVE_LAYERS, waveHeight } from '../lib/wave.js'

describe('waveHeight', () => {
  const end = 600

  it('is flat at the start of the bar and at the thumb', () => {
    for (const layer of WAVE_LAYERS) {
      for (const t of [0, 1.3, 7]) {
        expect(waveHeight(layer, 0, end, t)).toBe(0)
        expect(waveHeight(layer, end, end, t)).toBe(0)
        expect(waveHeight(layer, 1, end, t)).toBeLessThan(0.01)
        expect(waveHeight(layer, end - 1, end, t)).toBeLessThan(0.01)
      }
    }
  })

  it('stays within the layer height', () => {
    for (const layer of WAVE_LAYERS) {
      for (let x = 0; x <= end; x += 7) {
        const h = waveHeight(layer, x, end, 3.3)
        expect(h).toBeGreaterThanOrEqual(0)
        expect(h).toBeLessThanOrEqual(layer.height + 1e-9)
      }
    }
  })

  it('moves over time', () => {
    const [layer] = WAVE_LAYERS
    expect(waveHeight(layer, 300, end, 0)).not.toBeCloseTo(
      waveHeight(layer, 300, end, 2)
    )
  })

  it('draws nothing when nothing has played', () => {
    expect(waveHeight(WAVE_LAYERS[0], 0, 0, 1)).toBe(0)
  })
})
