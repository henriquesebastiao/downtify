// Piece-by-piece playback of stream tracks with the Media Source
// Extensions: the player behind a song that isn't downloaded yet.
//
// One piece is CHUNK_SECONDS of MP3 (`GET /api/stream/chunk`), every
// browser appends it, and junctions stay ~20 s apart. Playback starts as
// soon as the first piece lands, the next pieces arrive while it plays,
// and a start - or a seek into a part that isn't loaded yet - only ever
// costs one small fetch instead of the whole track.
//
// Imported by the player only; song rows never touch this directly.
import API from '/src/model/api'
import { videoIdFor } from '/src/model/streamResolve'

export const CHUNK_SECONDS = 20
const MIME = 'audio/mpeg'
// While this much is left of what's buffered, the pieces after it are
// already on their way.
const FETCH_AHEAD_SECONDS = 8
// Buffered audio this far behind the playhead is dropped.
const EVICT_BEHIND_SECONDS = 60
// A piece smaller than this is the tail of the track, when its total
// length isn't known at all.
const SHORT_CHUNK_BYTES = 100 * 1024
// Fetched pieces kept per video, so going back (or replaying) refetches
// nothing. Memory only, bounded.
const MAX_CACHED_CHUNKS = 16

export function chunkingSupported() {
  try {
    return (
      typeof MediaSource !== 'undefined' &&
      typeof MediaSource.isTypeSupported === 'function' &&
      MediaSource.isTypeSupported(MIME)
    )
  } catch {
    return false
  }
}

export function chunkIndexFor(seconds) {
  return Math.max(0, Math.floor(Number(seconds || 0) / CHUNK_SECONDS))
}

const chunkCache = new Map()

/** Drop cached pieces (tests; the player never calls this). */
export function clearChunkCache() {
  chunkCache.clear()
}

function cacheKey(videoId, index) {
  return `${videoId}:${index}`
}

function rememberChunk(videoId, index, chunk) {
  chunkCache.set(cacheKey(videoId, index), chunk)
  while (chunkCache.size > MAX_CACHED_CHUNKS) {
    chunkCache.delete(chunkCache.keys().next().value)
  }
}

/**
 * One piece of `videoId` from `start` seconds in: `{data, start,
 * duration}` (`duration` is the whole track when the backend knows
 * it). Cached in memory, abortable, retried once by the caller.
 */
export async function fetchChunk(videoId, start, { signal } = {}) {
  const index = chunkIndexFor(start)
  const cached = chunkCache.get(cacheKey(videoId, index))
  if (cached) return cached
  const res = await API.getStreamChunk(videoId, index * CHUNK_SECONDS, {
    signal,
  })
  const chunk = {
    data: res.data,
    start: Number.isFinite(res.start) ? res.start : index * CHUNK_SECONDS,
    duration: Number(res.duration) || 0,
  }
  if (!chunk.data || chunk.data.byteLength === 0) {
    throw new Error('emptychunk')
  }
  rememberChunk(videoId, index, chunk)
  return chunk
}

/** The video id to play chunks of, preferring the track's own. */
export async function ensureVideoId(track) {
  const direct = String(track?.video_id || '').trim()
  if (/^[A-Za-z0-9_-]{11}$/.test(direct)) return direct
  return videoIdFor(track)
}

/**
 * Get the next track ready while the current one plays: its video id,
 * whole length and first piece. `{ videoId, duration }`, or `null`
 * when it can't be prepared (advancing retries, silently until then).
 */
export async function prepareTrack(track) {
  try {
    const videoId = await ensureVideoId(track)
    const first = await fetchChunk(videoId, 0)
    return { videoId, duration: first.duration || 0 }
  } catch {
    return null
  }
}

/**
 * A playback session driving `audio` for one streamed track. The
 * player creates it when such a track starts and drops it on any
 * track change, stop or new queue:
 *
 * - `await start()` attaches the Media Source and plays piece 0;
 * - `ensureTime(t)` (from `timeupdate`) fetches ahead;
 * - `await seekTo(t)` jumps, fetching the piece first when needed;
 * - `detach()` aborts everything and releases the object URL.
 */
export function createChunkSession(audio, { videoId, total }) {
  const session = {
    videoId,
    total: Number(total) || 0,
    audio,
    media: null,
    buffer: null,
    objectUrl: '',
    ops: [],
    fetching: new Map(),
    appended: new Set(),
    offset: 0,
    started: false,
    ended: false,
    detached: false,
    fatal: null,
  }

  function bufferedEnd() {
    try {
      const ranges = session.audio.buffered
      return ranges.length ? ranges.end(ranges.length - 1) : 0
    } catch {
      return 0
    }
  }

  function bufferedStart() {
    try {
      const ranges = session.audio.buffered
      return ranges.length ? ranges.start(0) : 0
    } catch {
      return 0
    }
  }

  function pump() {
    if (session.detached || !session.buffer || session.buffer.updating) return
    const op = session.ops.shift()
    if (!op) return
    try {
      op()
    } catch {
      // A failed append (evicted mid-op, detached source) drops the
      // rest of the queue: the next ensureTime rebuilds it.
      session.ops.length = 0
    }
  }

  function onUpdateEnd() {
    pump()
  }

  function enqueueAppend(index, data) {
    session.ops.push(() => {
      if (session.detached) return
      if (session.buffer.updating) {
        session.ops.unshift(() => enqueueAppend(index, data))
        return
      }
      if (session.offset !== index * CHUNK_SECONDS) {
        session.buffer.timestampOffset = index * CHUNK_SECONDS
        session.offset = index * CHUNK_SECONDS
      }
      session.buffer.appendBuffer(data)
      session.appended.add(index)
      evictBehind()
      maybeEnd(index, data.byteLength)
    })
    pump()
  }

  function maybeEnd(index, bytes) {
    if (session.ended || session.detached) return
    const coversEnd =
      (session.total > 0 && (index + 1) * CHUNK_SECONDS >= session.total) ||
      (session.total <= 0 && bytes < SHORT_CHUNK_BYTES)
    if (!coversEnd) return
    session.ops.push(() => {
      if (session.detached || session.ended) return
      try {
        if (session.media.readyState === 'open') session.media.endOfStream()
        session.ended = true
      } catch {
        // Already ended while an op was queued.
      }
    })
    pump()
  }

  function evictBehind() {
    if (session.detached) return
    const position = session.audio.currentTime || 0
    const horizon = position - EVICT_BEHIND_SECONDS
    if (bufferedStart() >= horizon) return
    const from = Math.max(0, bufferedStart())
    session.ops.push(() => {
      if (session.detached) return
      try {
        session.buffer.remove(from, horizon)
      } catch {
        // Ranges shift under concurrent appends; next time then.
      }
      for (const index of [...session.appended]) {
        if ((index + 1) * CHUNK_SECONDS <= horizon) {
          session.appended.delete(index)
        }
      }
    })
    pump()
  }

  function missingAround(position) {
    const end =
      session.total > 0
        ? Math.min(position + FETCH_AHEAD_SECONDS, session.total)
        : position + FETCH_AHEAD_SECONDS
    const missing = []
    for (
      let index = chunkIndexFor(position);
      index * CHUNK_SECONDS < end;
      index++
    ) {
      if (!session.appended.has(index) && !session.fetching.has(index)) {
        missing.push(index)
      }
    }
    return missing
  }

  async function fetchIndex(index) {
    if (
      session.detached ||
      session.appended.has(index) ||
      session.fetching.has(index)
    ) {
      return
    }
    const controller = new AbortController()
    session.fetching.set(index, controller)
    try {
      const chunk = await fetchChunk(session.videoId, index * CHUNK_SECONDS, {
        signal: controller.signal,
      })
      if (session.detached) return
      if (chunk.duration > 0 && session.total <= 0) {
        session.total = chunk.duration
        try {
          if (session.media.readyState === 'open') {
            session.media.duration = chunk.duration
          }
        } catch {
          // Duration stays unknown; the tail is found by size.
        }
      }
      enqueueAppend(index, chunk.data)
    } catch (error) {
      if (session.detached) return
      if (error?.name === 'AbortError' || signalAborted(controller)) return
      session.fatal = error
    } finally {
      session.fetching.delete(index)
    }
  }

  function signalAborted(controller) {
    try {
      return controller.signal.aborted
    } catch {
      return false
    }
  }

  async function start() {
    const media = new MediaSource()
    session.media = media
    session.objectUrl = URL.createObjectURL(media)
    session.audio.src = session.objectUrl
    await new Promise((resolve, reject) => {
      const done = () => {
        media.removeEventListener('sourceopen', done)
        resolve()
      }
      media.addEventListener('sourceopen', done)
      // A source that never opens is a dead track, not a hang.
      setTimeout(() => {
        media.removeEventListener('sourceopen', done)
        reject(new Error('nosourceopen'))
      }, 15000)
    })
    if (session.detached) throw new Error('detached')
    if (session.total > 0) {
      try {
        media.duration = session.total
      } catch {
        // Set from the first piece instead.
      }
    }
    session.buffer = media.addSourceBuffer(MIME)
    session.buffer.addEventListener('updateend', onUpdateEnd)
    await fetchIndex(0)
    if (session.detached) throw new Error('detached')
    if (session.fatal) throw session.fatal
    // Piece 0 is queued; playback starts once the browser has it.
    await session.audio.play().catch(() => {})
  }

  // Called from `timeupdate`: keep pieces ahead of the playhead.
  function ensureTime(position) {
    if (session.detached || session.ended) return
    for (const index of missingAround(position)) {
      void fetchIndex(index)
    }
  }

  // Jump to `seconds`, fetching its piece first when nothing covers it.
  async function seekTo(seconds) {
    if (session.detached) throw new Error('detached')
    const target = Math.max(0, seconds)
    if (covers(target)) {
      session.audio.currentTime = target
      ensureTime(target)
      return
    }
    for (const [, controller] of session.fetching) {
      try {
        controller.abort()
      } catch {
        // Already settled.
      }
    }
    session.fetching.clear()
    session.ops.length = 0
    const index = chunkIndexFor(target)
    const controller = new AbortController()
    session.fetching.set(index, controller)
    let chunk = null
    try {
      chunk = await fetchChunk(session.videoId, index * CHUNK_SECONDS, {
        signal: controller.signal,
      })
    } finally {
      if (session.fetching.get(index) === controller) {
        session.fetching.delete(index)
      }
    }
    if (session.detached) throw new Error('detached')
    if (chunk.duration > 0 && session.total <= 0) {
      session.total = chunk.duration
    }
    enqueueAppend(index, chunk.data)
    await waitForAppended(index)
    if (session.detached) throw new Error('detached')
    session.audio.currentTime = target
    ensureTime(target)
  }

  function covers(seconds) {
    try {
      const ranges = session.audio.buffered
      for (let i = 0; i < ranges.length; i++) {
        if (ranges.start(i) - 1 <= seconds && seconds <= ranges.end(i)) {
          return true
        }
      }
    } catch {
      return false
    }
    return false
  }

  function waitForAppended(index) {
    if (session.appended.has(index)) return Promise.resolve()
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('appendtimeout')), 15000)
      const check = () => {
        if (session.detached) {
          clearTimeout(timer)
          reject(new Error('detached'))
        } else if (session.appended.has(index)) {
          clearTimeout(timer)
          resolve()
        } else if (session.fatal) {
          clearTimeout(timer)
          reject(session.fatal)
        } else {
          setTimeout(check, 50)
        }
      }
      check()
    })
  }

  function detach() {
    session.detached = true
    for (const [, controller] of session.fetching) {
      try {
        controller.abort()
      } catch {
        // Already settled.
      }
    }
    session.fetching.clear()
    session.ops.length = 0
    try {
      session.buffer?.removeEventListener('updateend', onUpdateEnd)
    } catch {
      // Never attached.
    }
    if (session.objectUrl) {
      try {
        URL.revokeObjectURL(session.objectUrl)
      } catch {
        // Already gone.
      }
      session.objectUrl = ''
    }
    session.buffer = null
    session.media = null
  }

  return {
    start,
    ensureTime,
    seekTo,
    detach,
    bufferedEnd,
    // Observable for tests; the player never reads it.
    get media() {
      return session.media
    },
    isEnded: () => session.ended && !session.detached,
    get videoId() {
      return session.videoId
    },
    get total() {
      return session.total
    },
  }
}
