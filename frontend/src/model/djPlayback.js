// A network notification is not a playback break while decoded audio is buffered.
export function isPlaybackInterruption(type, media) {
  if (type === 'stalled') return Boolean(media && !media.paused && media.readyState < 3)
  return ['waiting', 'seeking', 'pause'].includes(type)
}
