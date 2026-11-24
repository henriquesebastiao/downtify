// Music videos in Now playing (issue #680): the video plays muted next to
// the song, which keeps the sound (equalizer, normalization, lyrics
// timing all follow the audio). These rules keep the picture in step.

/** How far (s) the picture may drift from the song before it jumps. */
export const DRIFT_LIMIT = 0.35

/**
 * What to do to the <video> so it shows the moment the song is at:
 * `{ seek, play, pause }` — `seek` a time or null. Past the video's end
 * (a song longer than its video) it holds the last frame.
 */
export function videoSyncAction({
  audioTime = 0,
  videoTime = 0,
  duration = 0,
  playing = false,
  videoPaused = true,
}) {
  const end = Number(duration) || 0
  const target = Math.max(0, Number(audioTime) || 0)
  if (end && target >= end) {
    return { seek: null, play: false, pause: !videoPaused }
  }
  const drift = Math.abs(target - (Number(videoTime) || 0))
  return {
    seek: drift > DRIFT_LIMIT ? target : null,
    play: playing && videoPaused,
    pause: !playing && !videoPaused,
  }
}

/**
 * Where to put a video whose picture has black bars burnt in, so the
 * picture alone covers a `boxWidth` x `boxHeight` area (like
 * `object-fit: cover`, but on the picture instead of the whole frame):
 * `{left, top, width, height}` in px, or null to just cover the box
 * (no bars, or nothing measured yet).
 */
export function coverPicture(crop, boxWidth, boxHeight) {
  if (!crop || !(boxWidth > 0) || !(boxHeight > 0)) return null
  const {
    width,
    height,
    x,
    y,
    video_width: frameW,
    video_height: frameH,
  } = crop
  if (!(width > 0 && height > 0 && frameW > 0 && frameH > 0)) return null
  const scale = Math.max(boxWidth / width, boxHeight / height)
  return {
    left: boxWidth / 2 - (x + width / 2) * scale,
    top: boxHeight / 2 - (y + height / 2) * scale,
    width: frameW * scale,
    height: frameH * scale,
  }
}
