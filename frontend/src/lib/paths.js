// URLs for library files. Pure (no API client import), so models and
// tests can use them without opening the app's WebSocket.

// slskd downloads left in place live outside the downloads folder, so
// the '/downloads' static mount can't serve them; '/media' resolves both.
export const SLSKD_LIBRARY_PREFIX = 'slskd/'

/**
 * Encode each path segment on its own so '/' separators survive —
 * playlist downloads land under '<playlist>/<song>.mp3'.
 */
export function encodePath(fileName) {
  return String(fileName || '')
    .split('/')
    .map(encodeURIComponent)
    .join('/')
}

export function fileURL(fileName) {
  const path = String(fileName || '')
  if (path.startsWith(SLSKD_LIBRARY_PREFIX)) {
    return `/media/${encodePath(path)}`
  }
  return `/downloads/${encodePath(path)}`
}

export function coverURL(fileName) {
  return `/cover?file=${encodeURIComponent(fileName)}`
}

/** Last path segment, decoded — what the browser save dialog shows. */
export function saveName(fileNameOrURL) {
  const parts = String(fileNameOrURL || '')
    .split('/')
    .filter(Boolean)
  const last = parts[parts.length - 1]
  if (!last) return 'download'
  try {
    return decodeURIComponent(last)
  } catch {
    return last
  }
}
