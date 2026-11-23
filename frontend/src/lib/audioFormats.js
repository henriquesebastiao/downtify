// The audio formats a user can keep out of the library: "Formats to
// avoid" (Settings > Downloads & files) and the Doctor's "Formats to
// convert". Same list and order as FORMATS in downtify/audio_formats.py.

export const FORMATS = [
  'flac',
  'wav',
  'aiff',
  'ape',
  'wv',
  'm4a',
  'ogg',
  'opus',
]

const LABELS = { wv: 'WavPack', ape: 'APE (Monkey’s Audio)' }

/** How a format is shown: its usual name. */
export function formatLabel(format) {
  return LABELS[format] || String(format || '').toUpperCase()
}

/**
 * The format a Downloads setting writes, as one of FORMATS ('' for MP3 or
 * "Original"): it can't be a format to avoid.
 */
export function downloadsFormat(format) {
  const value = String(format || '').toLowerCase()
  return FORMATS.includes(value) ? value : ''
}

/** Bytes saved converting files of `bytes` to an estimated `estimated`. */
export function savedBytes(bytes, estimated) {
  return Math.max(0, Number(bytes || 0) - Number(estimated || 0))
}
