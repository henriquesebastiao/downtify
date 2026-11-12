// What the Downtify window and its projected karaoke window say to each
// other over a BroadcastChannel: the stage pings, the host answers with
// the state, and sends it again whenever something changes.

export const STAGE_PING_MS = 2000
// A few missed pings: the other window is gone.
export const STAGE_TIMEOUT_MS = 6000

export function stageChannelName(id) {
  return `downtify-karaoke-${id}`
}

export function stageWindowName(id) {
  return `downtify-karaoke-window-${id}`
}

export function stagePath(baseUrl, id) {
  return `${baseUrl}/karaoke.html?host=${encodeURIComponent(id)}`
}

// Only plain values: the player's tracks are Vue proxies, which
// postMessage refuses to clone.
function stageTrack(track) {
  if (!track) return null
  return {
    file: track.file || '',
    title: track.title || '',
    artist: track.artist || '',
    album: track.album || '',
    cover: track.cover || '',
    hasCover: !!track.hasCover,
  }
}

export function stageState({ track, next, time, playing }) {
  return {
    type: 'state',
    track: stageTrack(track),
    next: stageTrack(next),
    time: time || 0,
    playing: !!playing,
  }
}
