// Replacing a library track's audio with a version picked by hand
// (downtify/audio_replace.py). Pure, so it's unit-testable.

/** How far a candidate's length is from the track's: '+12s', '−3s', ''. */
export function lengthDiff(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds))
    return ''
  const value = Math.round(Number(seconds))
  if (value === 0) return '±0s'
  return value > 0 ? `+${value}s` : `−${Math.abs(value)}s`
}

/** Whether a candidate is about as long as the track (within 3 s). */
export function sameLength(seconds) {
  return seconds !== null && seconds !== undefined && Math.abs(seconds) <= 3
}

/** Whether `track` (a library track) can have its audio replaced. */
export function canReplace(track) {
  if (!track?.file || track.isPodcast) return false
  return /\.(mp3|flac|m4a|ogg|opus)$/i.test(track.file)
}
