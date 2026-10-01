// Smaller Deezer images for display. Pure, so it's unit-testable.
//
// A Deezer cover or photo URL carries its size in its last path segment
// (`.../cover/<md5>/1000x1000-000000-80-0-0.jpg`), and the API's own size
// presets (`cover_small`/`_medium`/`_big`/`_xl`, 56/250/500/1000 px) are that
// same URL with only the size changed. So the medium one can be had from any
// of them without asking the API again.
//
// Display only: the `cover_url` a song carries is what gets embedded in the
// downloaded file, at the size Settings asks for - it must go to the queue
// untouched. Only what an <img> shows is swapped for this.

// Deezer's "medium" preset: sharp enough for the thumbnails and cards the
// app shows, a fraction of the bytes of the 500/1000 px ones.
export const DEEZER_MEDIUM = 250

const SIZED_URL =
  /^(https:\/\/[^/]+\.dzcdn\.net\/images\/[a-z]+\/[0-9a-f]+\/)(\d+)x(\d+)(-[^/]*)$/

/**
 * `url` at `size` px when it's a Deezer image bigger than that; anything
 * else (smaller already, another source, empty) comes back as it was.
 */
export function deezerImage(url, size = DEEZER_MEDIUM) {
  const text = String(url || '')
  const match = SIZED_URL.exec(text)
  if (!match || Number(match[2]) <= size) return url
  return `${match[1]}${size}x${size}${match[4]}`
}
