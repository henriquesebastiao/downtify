// Resolving a not-downloaded song to a playable stream URL. Pure apart
// from the two backend calls, and deliberately player-free, so the
// player itself can import it (resolving on advance) without a module
// cycle.
//
// Keep this import static: a dynamic `import('/src/model/api')` here
// carves the API client into its own chunk with a vendor->api edge that
// evaluates before init - the shipped app then dies on load with
// `TypeError: e is not a function` in the vendor chunk.
import API from '/src/model/api'

const VIDEO_ID_RE = /^[A-Za-z0-9_-]{11}$/

export function songArtist(song) {
  return String((song?.artists || [])[0] || song?.artist || '').trim()
}

export function songTitle(song) {
  return String(song?.name || song?.title || '').trim()
}

export function rowKey(song) {
  return `${songArtist(song)}|${songTitle(song)}`.toLowerCase()
}

/** This song's YouTube video id when it already carries one. */
export function directVideoId(song) {
  const direct = String(song?.youtube_id || '').trim()
  if (VIDEO_ID_RE.test(direct)) return direct
  const sid = String(song?.song_id || '').trim()
  return VIDEO_ID_RE.test(sid) ? sid : ''
}

/** The video id to stream: the song's own, else the first search hit. */
export async function videoIdFor(song) {
  const direct = directVideoId(song)
  if (direct) return direct
  const artist = songArtist(song)
  const title = songTitle(song)
  if (!artist || !title) throw new Error('noartistortitle')
  const res = await API.search(`${artist} ${title}`)
  for (const row of res.data || []) {
    const candidate = directVideoId(row)
    if (candidate) return candidate
  }
  throw new Error('nomatch')
}

/**
 * A fresh direct-audio URL for `track` (a player track with no `url`
 * yet). Short-lived: resolved on demand, never stored. Throws when
 * there is nothing to play.
 */
export async function resolveTrackUrl(track) {
  const videoId = await videoIdFor(track)
  const res = await API.getStreamUrl(videoId)
  const url = res.data?.url
  if (typeof url !== 'string' || !url.startsWith('https://')) {
    throw new Error('nourl')
  }
  return { url, videoId }
}
