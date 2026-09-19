// Display formatting shared across views. Pure, so it's unit-testable.

/** `184` -> `3:04`; `3725` -> `1:02:05`. */
export function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0:00'
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = String(total % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
}

/**
 * Coarse length of a whole album/playlist: `{ hours, minutes }`, with
 * minutes rounded so "2 h 31 min" style labels can be built by i18n.
 */
export function splitLength(seconds) {
  const minutes = Math.round((Number(seconds) || 0) / 60)
  return { hours: Math.floor(minutes / 60), minutes: minutes % 60 }
}

/**
 * The widest an "elapsed / total" clock can get for a track of `seconds`:
 * the total on both sides (the elapsed time never has more digits than
 * it), with every digit a "0". Rendered invisibly, it reserves the
 * clock's room so it never wraps and the controls beside it never shift
 * as it ticks. Digits are the widest at "0" in the UI font, and its
 * `tabular-nums` doesn't equalise them — its "1" is under half as wide —
 * so this is a real upper bound rather than a guess.
 */
export function widestClock(seconds) {
  const widest = formatDuration(seconds).replace(/\d/g, '0')
  return `${widest} / ${widest}`
}

const UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

/** `1536` -> `1.5 KB`, `62_400_000_000` -> `58.1 GB` (binary units). */
export function formatBytes(bytes) {
  let value = Number(bytes) || 0
  let unit = 0
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024
    unit += 1
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1
  return `${value.toFixed(digits)} ${UNITS[unit]}`
}

const RELATIVE_STEPS = [
  ['year', 365 * 24 * 3600],
  ['month', 30 * 24 * 3600],
  ['week', 7 * 24 * 3600],
  ['day', 24 * 3600],
  ['hour', 3600],
  ['minute', 60],
]

/**
 * "2 minutes ago" / "yesterday" in the UI language. `when` is epoch
 * seconds, epoch milliseconds or an ISO string.
 */
export function timeAgo(when, locale = 'en', now = Date.now()) {
  let ms
  if (typeof when === 'number') {
    ms = when < 1e12 ? when * 1000 : when
  } else {
    ms = new Date(when).getTime()
  }
  if (!Number.isFinite(ms) || ms <= 0) return ''
  const diff = Math.round((ms - now) / 1000)
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  for (const [unit, size] of RELATIVE_STEPS) {
    if (Math.abs(diff) >= size) {
      return rtf.format(Math.round(diff / size), unit)
    }
  }
  return rtf.format(0, 'minute')
}

/** Upper-cased extension of a library path, e.g. `FLAC`. */
export function fileFormat(file) {
  const match = /\.([a-z0-9]+)$/i.exec(String(file || ''))
  return match ? match[1].toUpperCase() : ''
}

/** Stable pseudo-random hue for placeholder art. */
export function hueFor(text) {
  let hash = 0
  for (const char of String(text || '')) {
    hash = (hash * 31 + char.codePointAt(0)) >>> 0
  }
  return hash % 360
}

/** First letters of up to two words: "The Night Owls" -> "TN". */
export function initials(text) {
  return String(text || '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join('')
}
