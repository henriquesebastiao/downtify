// Saved links (issue #731): playlist and album links kept in Library >
// Playlists to stream, a bookmark per account. Pure, so what the link
// page offers and how the list changes are unit-testable without a
// browser. The server reads every link again and keeps only the ones it
// can stream (downtify/saved_links.py).

/** The services whose playlists and albums can be saved, by name. */
export const SAVED_LINK_SOURCES = {
  spotify: 'Spotify',
  youtube: 'YouTube Music',
  deezer: 'Deezer',
}

/**
 * Whether the link page offers Save: `details` (what the link resolved
 * to) is a playlist or an album, and `input` (`classifyInput` of the
 * link) a Spotify, Deezer or YouTube Music link.
 */
export function canSaveLink(details, input) {
  return (
    (details?.kind === 'playlist' || details?.kind === 'album') &&
    input?.type === 'link' &&
    Object.hasOwn(SAVED_LINK_SOURCES, input.source)
  )
}

/**
 * What Save sends: the link as it was opened (the server stores it under
 * its canonical URL), the name, and a cover - the collection's own, else
 * its first song's, as the page's mosaic starts with it.
 */
export function savedLinkPayload(details, url) {
  const cover =
    details?.cover_url ||
    (details?.tracks || []).map((song) => song?.cover_url).find(Boolean) ||
    ''
  return { url, name: details?.name || '', cover }
}

/**
 * `links` with `link` saved: a new one first (newest first, like the
 * server), one already there updated where it is. Never mutates.
 */
export function withSavedLink(links, link) {
  const list = Array.isArray(links) ? links : []
  if (!link?.url) return list
  if (!list.some((item) => item.url === link.url)) return [link, ...list]
  return list.map((item) => (item.url === link.url ? link : item))
}

/** `links` without the one saved under `url`. Never mutates. */
export function withoutSavedLink(links, url) {
  return (Array.isArray(links) ? links : []).filter((item) => item.url !== url)
}

/** The line under a saved link's name: "Spotify · Playlist". */
export function savedLinkSubtitle(link, t) {
  const kind = link?.kind === 'album' ? 'album' : 'playlist'
  return [SAVED_LINK_SOURCES[link?.source], t(`link.kind.${kind}`)]
    .filter(Boolean)
    .join(' · ')
}
