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
 * The server URL streaming `track` (a player track with no `url` yet):
 * the backend downloads the audio once into its stream cache and serves
 * it from there, so playback never depends on the browser reaching
 * YouTube itself. Throws when there is nothing to play.
 */
export async function resolveTrackUrl(track) {
  const videoId = await videoIdFor(track)
  return {
    url: `/api/stream/file?video_id=${encodeURIComponent(videoId)}`,
    videoId,
  }
}

/**
 * Warm the server cache for `track` without waiting for it, so skipping
 * to it starts instantly. Silent by design: a failed warm only means
 * the advance resolves on demand, with an error then.
 */
export async function prefetchServerCache(track) {
  try {
    await warmServerCache(await videoIdFor(track))
  } catch {
    // The advance resolves again and reports failures itself.
  }
}

/** Warm the server cache for a known video id (never throws). */
export async function warmServerCache(videoId) {
  try {
    await API.prefetchStream(videoId)
  } catch {
    // The advance resolves again and reports failures itself.
  }
}
