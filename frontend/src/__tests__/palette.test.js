import { describe, expect, it } from 'vitest'
import {
  extractPalette,
  hexToRgb,
  hslToRgb,
  mixRgb,
  rgbToHsl,
} from '../lib/palette.js'

function image(colors) {
  // colors: [[r, g, b, count, alpha?], ...] → flat RGBA array
  const data = []
  for (const [r, g, b, count, a = 255] of colors) {
    for (let i = 0; i < count; i++) data.push(r, g, b, a)
  }
  return new Uint8ClampedArray(data)
}

const hueOf = (hex) => rgbToHsl(hexToRgb(hex))[0]
const lightnessOf = (hex) => rgbToHsl(hexToRgb(hex))[2]

describe('hsl conversion', () => {
  it('round-trips', () => {
    for (const rgb of [
      [255, 0, 0],
      [18, 200, 90],
      [240, 180, 120],
      [128, 128, 128],
    ]) {
      const back = hslToRgb(rgbToHsl(rgb))
      back.forEach((v, i) =>
        expect(Math.abs(v - rgb[i])).toBeLessThanOrEqual(1)
      )
    }
  })
})

describe('extractPalette', () => {
  it('picks the dominant colourful hue over near-black pixels', () => {
    const palette = extractPalette(
      image([
        [5, 5, 5, 600],
        [235, 150, 70, 300], // orange
        [60, 90, 200, 80], // blue
      ])
    )
    expect(Math.abs(hueOf(palette.primary) - 30)).toBeLessThan(8)
    expect(Math.abs(hueOf(palette.secondary) - 225)).toBeLessThan(10)
  })

  it('is not fooled by tinted near-black pixels', () => {
    const palette = extractPalette(
      image([
        [7, 4, 10, 900], // almost black, slightly purple
        [16, 48, 80, 70], // dark blue
        [224, 208, 192, 30], // beige
      ])
    )
    expect(Math.abs(hueOf(palette.primary) - 210)).toBeLessThan(8)
    expect(Math.abs(hueOf(palette.secondary) - 30)).toBeLessThan(8)
  })

  it('keeps colours readable on the dark player', () => {
    const palette = extractPalette(image([[40, 10, 15, 500]]))
    expect(lightnessOf(palette.primary)).toBeGreaterThanOrEqual(0.59)
    expect(lightnessOf(palette.soft)).toBeGreaterThan(0.8)
    expect(lightnessOf(palette.background)).toBeLessThan(0.25)
  })

  it('does not invent a hue for greyscale artwork', () => {
    const palette = extractPalette(image([[120, 120, 120, 400]]))
    const [, s] = rgbToHsl(hexToRgb(palette.primary))
    expect(s).toBeLessThan(0.08)
  })

  it('ignores transparent pixels', () => {
    expect(extractPalette(image([[255, 0, 0, 50, 0]]))).toBeNull()
  })
})

describe('mixRgb', () => {
  it('blends linearly', () => {
    expect(mixRgb([0, 100, 200], [100, 100, 0], 0.5)).toEqual([50, 100, 100])
  })
})
