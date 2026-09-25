// The 30 s preview clip of a song that isn't downloaded yet. Pure, so it's
// unit-testable.

// What Spotify's preview clips last, for the progress before the browser
// has read the file's real length.
export const PREVIEW_SECONDS = 30

// The progress ring drawn around a row's play/pause button while its preview
// plays (a 24 px box, the number's place - see TrackDownPlay).
export const PREVIEW_RING_RADIUS = 10
export const PREVIEW_RING_LENGTH = 2 * Math.PI * PREVIEW_RING_RADIUS

/**
 * The song's preview clip, or '' when it has none. Only an https link is
 * handed to the audio element.
 */
export function previewUrl(song) {
  const url = song?.preview_url
  return typeof url === 'string' && url.startsWith('https://') ? url : ''
}

/** How far into the clip, from 0 to 1. */
export function previewRatio(time, duration) {
  const total =
    Number.isFinite(duration) && duration > 0 ? duration : PREVIEW_SECONDS
  const ratio = Number(time) / total
  return Number.isFinite(ratio) ? Math.min(1, Math.max(0, ratio)) : 0
}

/** The ring's `stroke-dashoffset` that draws `ratio` of it. */
export function ringOffset(ratio) {
  return PREVIEW_RING_LENGTH * (1 - ratio)
}
