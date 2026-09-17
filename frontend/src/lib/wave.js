// Shape of the soft waves drawn over the played part of the seek bar.

const TAU = Math.PI * 2

/** Wave layers, back to front. `color` names a palette entry. */
export const WAVE_LAYERS = [
  { color: 'soft', alpha: 0.5, height: 1, length: 230, speed: 0.55, phase: 0 },
  {
    color: 'secondary',
    alpha: 0.6,
    height: 0.72,
    length: 160,
    speed: -0.8,
    phase: 2.1,
  },
  {
    color: 'primary',
    alpha: 0.9,
    height: 0.42,
    length: 120,
    speed: 1.05,
    phase: 4.2,
  },
]

function smoothstep(edge, x) {
  const t = Math.min(1, Math.max(0, x / edge))
  return t * t * (3 - 2 * t)
}

/**
 * Height (0..1) of a layer at `x` px along a played length of `end` px,
 * at time `t` seconds. Waves taper to nothing at the start of the bar and
 * at the thumb, and rise in smooth, uneven hills.
 */
export function waveHeight(layer, x, end, t, taper = 36) {
  if (x <= 0 || x >= end) return 0
  const envelope = smoothstep(taper, x) * smoothstep(taper, end - x)
  const k = TAU / layer.length
  const n =
    0.62 * Math.sin(x * k + t * layer.speed + layer.phase) +
    0.38 * Math.sin(x * k * 1.93 - t * layer.speed * 0.7 + layer.phase * 1.7)
  const hill = ((n + 1) / 2) ** 2
  return envelope * hill * layer.height
}
