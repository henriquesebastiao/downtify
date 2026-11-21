import { playlistCoverURL } from '/src/lib/paths'

/**
 * The cover saved beside an M3U (``<name>.jpg`` next to ``<name>.m3u``),
 * served by ``/playlist-cover``. *version* changes the URL when a merge
 * may have replaced the picture, so the browser doesn't show an old one.
 */
export function playlistCoverOf(m3uPath, version = '') {
  const jpg = String(m3uPath || '').replace(/\.m3u8?$/i, '.jpg')
  if (!jpg || jpg === m3uPath) return ''
  const url = playlistCoverURL(jpg)
  return version ? `${url}&v=${encodeURIComponent(version)}` : url
}
