import { describe, expect, it } from 'vitest'
import {
  BANDS,
  GAIN_LIMIT,
  PREAMP_LIMIT,
  PRESETS,
  biquad,
  defaultSettings,
  formatFrequency,
  formatGain,
  headroomDb,
  magnitudeDb,
  matchPreset,
  parseSettings,
  presetGains,
  responseDb,
  responseFrequencies,
  responsePath,
  snapGain,
} from '../lib/equalizer.js'

const flat = BANDS.map(() => 0)

describe('bands and presets', () => {
  it('has ten octave-spaced bands with shelves at the ends', () => {
    expect(BANDS).toHaveLength(10)
    expect(BANDS[0].type).toBe('lowshelf')
    expect(BANDS.at(-1).type).toBe('highshelf')
    for (let i = 1; i < BANDS.length; i++) {
      const octaves = Math.log2(BANDS[i].frequency / BANDS[i - 1].frequency)
      expect(octaves).toBeCloseTo(1, 1)
    }
  })

  it('has one gain per band in every preset, within the limit', () => {
    const ids = PRESETS.map((p) => p.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids[0]).toBe('flat')
    for (const preset of PRESETS) {
      expect(preset.gains).toHaveLength(BANDS.length)
      for (const gain of preset.gains) {
        expect(Math.abs(gain)).toBeLessThanOrEqual(GAIN_LIMIT)
        expect(snapGain(gain)).toBe(gain)
      }
    }
  })

  it('keeps presets distinct from each other', () => {
    for (const preset of PRESETS) {
      expect(matchPreset(preset.gains)).toBe(preset.id)
    }
  })

  it('reports custom gains as custom', () => {
    const gains = [...presetGains('rock')]
    gains[3] += 0.5
    expect(matchPreset(gains)).toBe('custom')
  })

  it('falls back to flat for an unknown preset', () => {
    expect(presetGains('nope')).toEqual(flat)
  })
})

describe('snapGain', () => {
  it('rounds to half a dB and clamps', () => {
    expect(snapGain(2.26)).toBe(2.5)
    expect(snapGain(-0.2)).toBe(0)
    expect(Object.is(snapGain(-0.2), -0)).toBe(false)
    expect(snapGain(40)).toBe(GAIN_LIMIT)
    expect(snapGain(-40)).toBe(-GAIN_LIMIT)
    expect(snapGain('abc')).toBe(0)
    expect(snapGain(Number.NaN)).toBe(0)
  })
})

describe('formatting', () => {
  it('shortens frequencies', () => {
    expect(BANDS.map((b) => formatFrequency(b.frequency))).toEqual([
      '31',
      '62',
      '125',
      '250',
      '500',
      '1k',
      '2k',
      '4k',
      '8k',
      '16k',
    ])
    expect(formatFrequency(1500)).toBe('1.5k')
  })

  it('signs gains', () => {
    expect(formatGain(3)).toBe('+3 dB')
    expect(formatGain(-1.5)).toBe('−1.5 dB')
    expect(formatGain(0.01)).toBe('0 dB')
  })
})

describe('frequency response', () => {
  const rate = 48000

  it('is flat when every gain is 0', () => {
    const levels = responseDb(flat, responseFrequencies(40), rate)
    for (const db of levels) expect(Math.abs(db)).toBeLessThan(1e-9)
  })

  it('peaks by the band gain at the band centre', () => {
    const filter = biquad('peaking', 1000, 6, 1.41, rate)
    expect(magnitudeDb(filter, 1000, rate)).toBeCloseTo(6, 6)
    // Roughly half the boost an octave away.
    expect(magnitudeDb(filter, 2000, rate)).toBeGreaterThan(1)
    expect(magnitudeDb(filter, 2000, rate)).toBeLessThan(4)
  })

  it('shelves reach their gain far from the corner', () => {
    const low = biquad('lowshelf', 31, 8, 1, rate)
    expect(magnitudeDb(low, 5, rate)).toBeCloseTo(8, 1)
    expect(magnitudeDb(low, 5000, rate)).toBeCloseTo(0, 2)
    const high = biquad('highshelf', 16000, -8, 1, rate)
    expect(magnitudeDb(high, 23000, rate)).toBeLessThan(-6)
    expect(magnitudeDb(high, 200, rate)).toBeCloseTo(0, 2)
  })

  it('cuts only where the band is', () => {
    const gains = [...flat]
    gains[5] = -9
    const [at1k] = responseDb(gains, [1000], rate)
    const [at62] = responseDb(gains, [62], rate)
    expect(at1k).toBeCloseTo(-9, 1)
    expect(Math.abs(at62)).toBeLessThan(0.1)
  })
})

describe('headroomDb', () => {
  it('is 0 without boosts', () => {
    expect(headroomDb(flat)).toBe(0)
    expect(headroomDb(flat.map(() => -6))).toBe(0)
  })

  it('takes off the loudest point of the curve', () => {
    const gains = [...flat]
    gains[5] = 6
    expect(headroomDb(gains)).toBeCloseTo(-6, 1)
  })

  it('covers neighbouring boosts that add up', () => {
    const gains = [...flat]
    gains[4] = 6
    gains[5] = 6
    // Two overlapping boosts peak above either one.
    expect(headroomDb(gains)).toBeLessThan(-6.5)
    for (const db of responseDb(gains, responseFrequencies(200))) {
      expect(db + headroomDb(gains)).toBeLessThanOrEqual(1e-6)
    }
  })
})

describe('responsePath', () => {
  it('draws a flat line across the middle', () => {
    const path = responsePath(flat, { width: 400, height: 100 })
    const points = [...path.matchAll(/[ML]([\d.]+) ([\d.]+)/g)]
    expect(points.length).toBeGreaterThan(10)
    for (const [, x, y] of points) {
      expect(Number(y)).toBeCloseTo(50, 1)
      expect(Number(x)).toBeGreaterThanOrEqual(0)
      expect(Number(x)).toBeLessThanOrEqual(400.1)
    }
    expect(Number(points[0][1])).toBeCloseTo(0, 0)
    expect(Number(points.at(-1)[1])).toBeCloseTo(400, 0)
  })

  it('puts a boosted band above its column and clips at the edge', () => {
    const gains = [...flat]
    gains[5] = 12
    gains[4] = 12
    const path = responsePath(gains, { width: 400, height: 100 })
    const ys = [...path.matchAll(/[ML][\d.]+ ([\d.]+)/g)].map((m) => +m[1])
    expect(Math.min(...ys)).toBe(0)
    expect(Math.max(...ys)).toBeLessThanOrEqual(100)
  })
})

describe('parseSettings', () => {
  it('falls back to defaults for nothing or garbage', () => {
    for (const raw of [null, undefined, '', 'not json', '42', '[]', '{}']) {
      const settings = parseSettings(raw)
      expect(settings.gains).toEqual(flat)
      expect(settings.enabled).toBe(false)
      expect(settings.preamp).toBe(0)
    }
    expect(parseSettings(null)).toEqual(defaultSettings())
  })

  it('restores saved settings', () => {
    const saved = {
      enabled: true,
      preset: 'rock',
      gains: presetGains('rock'),
      preamp: -3,
    }
    expect(parseSettings(JSON.stringify(saved))).toEqual(saved)
  })

  it('cleans up out-of-range and wrong-length values', () => {
    const settings = parseSettings(
      JSON.stringify({
        enabled: 'yes',
        preset: 'rock',
        gains: [99, -99, 0.3, 0, 0, 0, 0, 0, 0, 'x'],
        preamp: 50,
      })
    )
    expect(settings.enabled).toBe(false)
    expect(settings.gains).toEqual([12, -12, 0.5, 0, 0, 0, 0, 0, 0, 0])
    expect(settings.preamp).toBe(PREAMP_LIMIT)
    // The gains no longer match "rock".
    expect(settings.preset).toBe('custom')
    expect(parseSettings({ gains: [1, 2] }).gains).toEqual(flat)
  })

  it('names the preset the gains match, whatever was stored', () => {
    const settings = parseSettings({
      preset: 'custom',
      gains: presetGains('vocal'),
    })
    expect(settings.preset).toBe('vocal')
  })
})
