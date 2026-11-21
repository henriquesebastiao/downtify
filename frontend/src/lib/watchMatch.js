// Which Monitor watch already follows an artist or a link, so a page can
// say "Watching" (and offer to stop) instead of offering to watch it again
// and getting "already being watched" back.
//
// A watch is matched by the id in its link or its key (`spotify_id`: a
// playlist's own id, `deezer:playlist:<id>` for Deezer, the YouTube Music
// channel for an artist) and, for an artist, by name too: a Spotify artist
// link is followed through the YouTube Music artist of the same name, so
// neither its link nor its key carries the Spotify id.

const LINK_IDS = [
  /open\.spotify\.com\/(?:intl-[a-z-]+\/)?(?:playlist|artist)\/([A-Za-z0-9]+)/i,
  /deezer\.com\/(?:[a-z]{2}\/)?playlist\/(\d+)/i,
  /[?&]list=([A-Za-z0-9_-]+)/,
  /youtube\.com\/channel\/(UC[A-Za-z0-9_-]+)/i,
]

/** The playlist or artist id a link names, '' when it names none. */
export function linkId(url) {
  const text = String(url || '')
  for (const pattern of LINK_IDS) {
    const match = pattern.exec(text)
    if (match) return match[1]
  }
  return ''
}

function watchIds(watch) {
  const key = String(watch?.spotify_id || '').replace(/^deezer:playlist:/, '')
  return new Set([linkId(watch?.url), key].filter(Boolean))
}

const fold = (text) =>
  String(text || '')
    .trim()
    .toLocaleLowerCase()

/**
 * The watch of `kind` ('artist' or 'playlist') that follows `url`, or the
 * artist called `name`; null when none does. With `userId`, only that
 * user's watches count: an admin lists everyone's, but may still add their
 * own watch of something another user watches.
 */
export function findWatch(
  watches,
  { kind, url = '', name = '', userId = null } = {}
) {
  const sameKind = (Array.isArray(watches) ? watches : []).filter(
    (watch) =>
      watch?.kind === kind && (userId == null || watch.user_id === userId)
  )
  const id = linkId(url)
  if (id) {
    const byLink = sameKind.find((watch) => watchIds(watch).has(id))
    if (byLink) return byLink
  }
  const wanted = fold(name)
  if (kind !== 'artist' || !wanted) return null
  return sameKind.find((watch) => fold(watch.name) === wanted) || null
}
