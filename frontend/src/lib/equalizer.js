// Graphic equalizer: bands, presets and the maths behind them. Pure
// functions only — the Web Audio wiring lives in model/equalizer.js.

// Ten octave-spaced ISO bands. The outer two are shelves, so they also
// move everything below 31 Hz / above 16 kHz.
export const BANDS = [
  { frequency: 31, type: 'lowshelf' },
  { frequency: 62, type: 'peaking' },
  { frequency: 125, type: 'peaking' },
  { frequency: 250, type: 'peaking' },
  { frequency: 500, type: 'peaking' },
  { frequency: 1000, type: 'peaking' },
  { frequency: 2000, type: 'peaking' },
  { frequency: 4000, type: 'peaking' },
  { frequency: 8000, type: 'peaking' },
  { frequency: 16000, type: 'highshelf' },
]

// One octave wide peaks, so neighbouring bands blend smoothly.
export const BAND_Q = 1.41

export const GAIN_LIMIT = 12
export const PREAMP_LIMIT = 12
export const GAIN_STEP = 0.5

const flat = BANDS.map(() => 0)

export const PRESETS = [
  { id: 'flat', gains: flat },
  { id: 'bassBoost', gains: [6, 5.5, 4.5, 2.5, 1, 0, 0, 0, 0, 0] },
  { id: 'trebleBoost', gains: [0, 0, 0, 0, 0, 0, 1.5, 3.5, 5, 6] },
  { id: 'vocal', gains: [-2, -2, -1, 0.5, 2.5, 4, 3.5, 2, 0.5, -1] },
  { id: 'rock', gains: [4.5, 3.5, 2, 0, -1.5, -1, 1, 2.5, 3.5, 4] },
  { id: 'electronic', gains: [5, 4, 1.5, 0, -2, 0.5, 0, 1.5, 4, 5] },
  { id: 'acoustic', gains: [3, 3, 1.5, 0, 0.5, 1, 2.5, 3, 2, 1] },
]

export const CUSTOM = 'custom'

export function clamp(value, limit) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 0
  return Math.max(-limit, Math.min(limit, n))
}

/** Rounds to the slider step and keeps within ±limit. */
export function snapGain(value, limit = GAIN_LIMIT) {
  return clamp(Math.round(Number(value) / GAIN_STEP) * GAIN_STEP, limit) || 0
}

export function presetGains(id) {
  return (PRESETS.find((preset) => preset.id === id) || PRESETS[0]).gains
}

/** The preset whose gains match exactly, or CUSTOM. */
export function matchPreset(gains) {
  const found = PRESETS.find((preset) =>
    preset.gains.every((gain, i) => Math.abs(gain - gains[i]) < 1e-6)
  )
  return found ? found.id : CUSTOM
}

/** 60 → "60", 1000 → "1k", 16000 → "16k". */
export function formatFrequency(hz) {
  if (hz < 1000) return String(hz)
  const k = hz / 1000
  return `${Number.isInteger(k) ? k : k.toFixed(1)}k`
}

/** +3 → "+3 dB", -1.5 → "−1.5 dB", 0 → "0 dB". */
export function formatGain(db) {
  const value = Math.round(db * 10) / 10
  if (value === 0) return '0 dB'
  const sign = value > 0 ? '+' : '−'
  return `${sign}${Math.abs(value)} dB`
}

export const dbToGain = (db) => 10 ** (db / 20)

// ── Frequency response ───────────────────────────────────────────────
// Biquad coefficients as the Web Audio spec defines them (the RBJ audio
// EQ cookbook), so the curve matches what BiquadFilterNode does.
export function biquad(type, frequency, gainDb, q, sampleRate) {
  const A = 10 ** (gainDb / 40)
  const w0 = (2 * Math.PI * frequency) / sampleRate
  const cos = Math.cos(w0)
  const sin = Math.sin(w0)
  if (type === 'peaking') {
    const alpha = sin / (2 * q)
    return {
      b: [1 + alpha * A, -2 * cos, 1 - alpha * A],
      a: [1 + alpha / A, -2 * cos, 1 - alpha / A],
    }
  }
  // Shelves: Web Audio fixes the slope at S = 1 and ignores Q.
  const alpha = (sin / 2) * Math.SQRT2
  const k = 2 * Math.sqrt(A) * alpha
  if (type === 'lowshelf') {
    return {
      b: [
        A * (A + 1 - (A - 1) * cos + k),
        2 * A * (A - 1 - (A + 1) * cos),
        A * (A + 1 - (A - 1) * cos - k),
      ],
      a: [
        A + 1 + (A - 1) * cos + k,
        -2 * (A - 1 + (A + 1) * cos),
        A + 1 + (A - 1) * cos - k,
      ],
    }
  }
  return {
    b: [
      A * (A + 1 + (A - 1) * cos + k),
      -2 * A * (A - 1 + (A + 1) * cos),
      A * (A + 1 + (A - 1) * cos - k),
    ],
    a: [
      A + 1 - (A - 1) * cos + k,
      2 * (A - 1 - (A + 1) * cos),
      A + 1 - (A - 1) * cos - k,
    ],
  }
}

/** |H(e^jw)| of one biquad, in dB. */
export function magnitudeDb({ b, a }, frequency, sampleRate) {
  const w = (2 * Math.PI * frequency) / sampleRate
  const c1 = Math.cos(w)
  const s1 = Math.sin(w)
  const c2 = Math.cos(2 * w)
  const s2 = Math.sin(2 * w)
  const numRe = b[0] + b[1] * c1 + b[2] * c2
  const numIm = -(b[1] * s1 + b[2] * s2)
  const denRe = a[0] + a[1] * c1 + a[2] * c2
  const denIm = -(a[1] * s1 + a[2] * s2)
  const num = numRe * numRe + numIm * numIm
  const den = denRe * denRe + denIm * denIm
  return 10 * Math.log10(num / den)
}

/** Log-spaced frequencies across the audible range. */
export function responseFrequencies(points = 96, from = 20, to = 20000) {
  const ratio = Math.log(to / from)
  return Array.from(
    { length: points },
    (_, i) => from * Math.exp((ratio * i) / (points - 1))
  )
}

/** Combined response of the whole bank, in dB, at each frequency. */
export function responseDb(gains, frequencies, sampleRate = 48000) {
  const filters = BANDS.map((band, i) =>
    biquad(band.type, band.frequency, gains[i] || 0, BAND_Q, sampleRate)
  )
  return frequencies.map((f) =>
    filters.reduce((sum, filter) => sum + magnitudeDb(filter, f, sampleRate), 0)
  )
}

/**
 * Gain the preamp takes off automatically so the loudest point of the
 * curve stays at 0 dB: boosting bands then reshapes the sound instead of
 * pushing it into clipping.
 */
export function headroomDb(gains, sampleRate = 48000) {
  if (!gains.some((gain) => gain > 0)) return 0
  const peak = Math.max(
    ...responseDb(gains, responseFrequencies(160), sampleRate)
  )
  return peak > 0 ? -peak : 0
}

/**
 * SVG path of the response curve, drawn over a row of equal-width band
 * columns (the bands are an octave apart, so octaves map to columns).
 * `limit` dB is the top/bottom edge; the curve is clipped there.
 */
export function responsePath(
  gains,
  { width, height, limit = GAIN_LIMIT, sampleRate = 48000, points = 120 }
) {
  const first = Math.log2(BANDS[0].frequency)
  const span = Math.log2(BANDS.at(-1).frequency) - first
  const column = width / BANDS.length
  const toX = (f) =>
    column / 2 + ((Math.log2(f) - first) / span) * (width - column)
  const toY = (db) => {
    const clamped = Math.max(-limit, Math.min(limit, db))
    return height / 2 - (clamped / limit) * (height / 2)
  }
  // Frequencies whose x lands inside the box.
  const low = 2 ** (first - (span * (column / 2)) / (width - column))
  const high = 2 ** (first + span + (span * (column / 2)) / (width - column))
  const freqs = responseFrequencies(points, low, Math.min(high, sampleRate / 2))
  const levels = responseDb(gains, freqs, sampleRate)
  return freqs
    .map((f, i) => {
      const x = toX(f).toFixed(1)
      const y = toY(levels[i]).toFixed(1)
      return `${i ? 'L' : 'M'}${x} ${y}`
    })
    .join(' ')
}

// ── Saved settings ───────────────────────────────────────────────────
export function defaultSettings() {
  return { enabled: false, preset: 'flat', gains: [...flat], preamp: 0 }
}

/** Whatever was stored (possibly nothing, or garbage) → valid settings. */
export function parseSettings(raw) {
  let data
  try {
    data = typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch {
    return defaultSettings()
  }
  if (!data || typeof data !== 'object') return defaultSettings()
  const gains =
    Array.isArray(data.gains) && data.gains.length === BANDS.length
      ? data.gains.map((gain) => snapGain(gain))
      : [...flat]
  const known = PRESETS.some((preset) => preset.id === data.preset)
  return {
    enabled: data.enabled === true,
    // A preset name only sticks if the gains still match it.
    preset:
      known && matchPreset(gains) === data.preset
        ? data.preset
        : matchPreset(gains),
    gains,
    preamp: snapGain(data.preamp, PREAMP_LIMIT),
  }
}
