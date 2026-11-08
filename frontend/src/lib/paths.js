// URLs for library files. Pure (no API client import), so models and
// tests can use them without opening the app's WebSocket.

// slskd downloads left in place live outside the downloads folder, so
// the '/downloads' static mount can't serve them; '/media' resolves both.
export const SLSKD_LIBRARY_PREFIX = 'slskd/'
export const EXTERNAL_LIBRARY_PREFIX = 'ext/'

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
  if (
    path.startsWith(SLSKD_LIBRARY_PREFIX) ||
    path.startsWith(EXTERNAL_LIBRARY_PREFIX)
  ) {
    return `/media/${encodePath(path)}`
  }
  return `/downloads/${encodePath(path)}`
}

export function coverURL(fileName) {
  return `/cover?file=${encodeURIComponent(fileName)}`
}

/** The cover sizes the server keeps scaled copies of (`/cover?size=`). */
export const COVER_SIZES = [150, 300, 600]

/**
 * A library cover URL (see `coverURL`) at a smaller size, for grids and
 * lists that show it small: a full picture is ~640 px and ~1.6 MB once
 * decoded, and a Library grid shows thousands. Any other URL (playlist
 * sidecars, remote images) comes back unchanged.
 */
export function sizedCoverURL(url, size) {
  const text = String(url || '')
  if (!size || !text.startsWith('/cover?') || /[?&]size=/.test(text)) {
    return text
  }
  return `${text}&size=${size}`
}

/**
 * A playlist's own cover image — the sidecar saved next to its M3U,
 * not a cover read out of a track's tags, so it has its own endpoint.
 */
export function playlistCoverURL(fileName) {
  if (!fileName) return ''
  return `/playlist-cover?file=${encodeURIComponent(fileName)}`
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
