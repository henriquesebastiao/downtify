// DISPLAY-ONLY photos for artists that have no saved photo: the related
// artists of the artist page, the Library's artists grid, the artist
// page's own round photo and the monitored artists list.
//
// The URL below is served by the backend's photo proxy, which relays
// Deezer's picture and forgets it (the browser caches it for three hours).
// Use it for an <img> on screen and nowhere else: never save, upload or
// copy what it returns into an artist's photo/banner, and never call it
// for an artist that already has a saved photo — that one comes from
// `getArtistArt`/`getArtistArtBulk` (ask those first, as LibraryView does;
// the search page never uses this: its artists bring their own picture).
// Pure (no API client import), like
// paths.js.
import { versionedArtUrl } from './artistArt'

export function proxiedArtistPhotoUrl(name) {
  const text = String(name || '').trim()
  if (!text) return ''
  return `/api/artists/photo-proxy?name=${encodeURIComponent(text)}`
}

/**
 * What an artist's picture shows on a grid or list, as the `{ cover,
 * fallback }` a CoverArt takes for `src`/`fallback`:
 *
 * - the saved photo (`entry`, one artist's `getArtistArtBulk` answer) when
 *   there is one;
 * - until that lookup has answered (`loaded` false) just `fallback`, with no
 *   proxy request - the artist might turn out to have a saved photo;
 * - otherwise the proxy's photo, with `fallback` (a picture known to exist,
 *   like a track's cover) behind it for an artist the proxy has none for.
 */
export function artistPhotoSource(name, entry, loaded, fallback = '') {
  const behind = fallback || ''
  const saved = versionedArtUrl(entry?.photo_url, entry?.photo_version)
  if (saved) return { cover: saved, fallback: '' }
  if (!loaded) return { cover: behind, fallback: '' }
  return { cover: proxiedArtistPhotoUrl(name), fallback: behind }
}
