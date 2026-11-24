// Lyrics for the Now playing view (GET /lyrics), cached per file.
import API from '/src/model/api'
import { parseLrc } from '/src/lib/lrc'

const cache = new Map()

/** Resolves `{ lines: [{time, text}], plain: string }` for a track. */
export function loadLyrics(file) {
  if (!file) return Promise.resolve({ lines: [], plain: '' })
  if (!cache.has(file)) {
    cache.set(
      file,
      API.getLyrics(file)
        .then((res) => ({
          lines: parseLrc(res.data?.synced),
          plain: String(res.data?.plain || ''),
        }))
        .catch(() => {
          cache.delete(file)
          return { lines: [], plain: '' }
        })
    )
  }
  return cache.get(file)
}

/**
 * Save a timing fix: the song's synced lyrics move `offsetMs` later
 * (sooner when negative). Resolves the new `{ lines, plain }`, which
 * also replace the cached ones; rejects with the request's error.
 */
export async function shiftLyrics(file, offsetMs) {
  const res = await API.shiftLyrics(file, Math.round(offsetMs))
  const previous = await (cache.get(file) || Promise.resolve(null))
  const result = {
    lines: parseLrc(res.data?.synced),
    plain: previous?.plain || '',
  }
  cache.set(file, Promise.resolve(result))
  return result
}
