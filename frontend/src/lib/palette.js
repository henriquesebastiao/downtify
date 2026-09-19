// Colours picked from album artwork, tuned to read well on the dark
// Now playing screen. Pure functions: the caller supplies RGBA pixels.

export function rgbToHsl([r, g, b]) {
  r /= 255
  g /= 255
  b /= 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  let h
  if (max === r) h = (g - b) / d + (g < b ? 6 : 0)
  else if (max === g) h = (b - r) / d + 2
  else h = (r - g) / d + 4
  return [h * 60, s, l]
}

export function hslToRgb([h, s, l]) {
  const k = (n) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1))
  return [f(0), f(8), f(4)].map((v) => Math.round(v * 255))
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

function hueDistance(a, b) {
  const d = Math.abs(a - b) % 360
  return d > 180 ? 360 - d : d
}

/** Groups pixels into coarse colour buckets, most common first. */
function buckets(pixels) {
  const map = new Map()
  for (let i = 0; i + 3 < pixels.length; i += 4) {
    if (pixels[i + 3] < 125) continue
    const r = pixels[i]
    const g = pixels[i + 1]
    const b = pixels[i + 2]
    const key = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
    const bucket = map.get(key)
    if (bucket) {
      bucket.count += 1
      bucket.sum[0] += r
      bucket.sum[1] += g
      bucket.sum[2] += b
    } else {
      map.set(key, { count: 1, sum: [r, g, b] })
    }
  }
  return [...map.values()].map(({ count, sum }) => {
    const rgb = sum.map((v) => Math.round(v / count))
    return { count, rgb, hsl: rgbToHsl(rgb) }
  })
}

// Prefer colours that are common *and* visibly colourful. HSL saturation
// alone runs high on near-black pixels, so weigh by chroma instead.
const isExtreme = (l) => l < 0.1 || l > 0.95

function score({ count, hsl: [, s, l] }) {
  const chroma = s * (1 - Math.abs(2 * l - 1))
  const tone = isExtreme(l) ? 0.05 : 1 - Math.abs(l - 0.5)
  return count * (0.15 + chroma * 2) * tone
}

const toHex = (rgb) =>
  `#${rgb.map((v) => v.toString(16).padStart(2, '0')).join('')}`

/** A hue/saturation reshaped to a fixed lightness range. */
function tune([h, s, l], { minL, maxL, minS = 0, maxS = 1 }) {
  // Near-grey artwork stays grey instead of being tinted a random hue.
  const sat = s < 0.08 ? s : clamp(s, minS, maxS)
  return toHex(hslToRgb([h, sat, clamp(l, minL, maxL)]))
}

/**
 * RGBA pixel data → `{ primary, secondary, soft, background }` hex
 * colours, or null when the image has no opaque pixels.
 *
 * - primary: the progress fill and front wave
 * - secondary: a second wave, a contrasting colour from the artwork
 * - soft: a light tint for the back wave and the thumb
 * - background: a deep shade for the screen behind the blurred artwork
 */
export function extractPalette(pixels) {
  const ranked = buckets(pixels).sort((a, b) => score(b) - score(a))
  if (!ranked.length) return null

  const main = ranked[0]
  const [h, s, l] = main.hsl
  const other = ranked.find(
    (c) =>
      c !== main &&
      !isExtreme(c.hsl[2]) &&
      c.count >= main.count * 0.08 &&
      (hueDistance(c.hsl[0], h) > 28 || Math.abs(c.hsl[2] - l) > 0.25)
  )
  const alt = other ? other.hsl : [(h + 24) % 360, s, l - 0.15]

  return {
    primary: tune([h, s, l], { minL: 0.6, maxL: 0.76, minS: 0.45 }),
    secondary: tune(alt, { minL: 0.5, maxL: 0.7, minS: 0.35 }),
    soft: tune([h, s * 0.7, 0.86], { minL: 0.84, maxL: 0.9, maxS: 0.7 }),
    background: tune([h, s, 0.2], { minL: 0.16, maxL: 0.22, maxS: 0.45 }),
  }
}

export function hexToRgb(hex) {
  const n = Number.parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** Linear blend between two [r, g, b] colours. */
export function mixRgb(from, to, amount) {
  return from.map((v, i) => v + (to[i] - v) * amount)
}
