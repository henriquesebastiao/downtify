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
