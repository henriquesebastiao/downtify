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
// Discover and the Finder do, handing it the Deezer picture they already
// have (`knownArtistPhoto`), so a saved photo shows instead when there is one.
// Pure (no API client import), like
// paths.js.
import { versionedArtUrl } from './artistArt'

/**
 * `text` as base64url (RFC 4648 section 5, no padding): letters, digits,
 * `-` and `_` only, so a whole address fits in a query value as it is.
 */
export function base64Url(text) {
  let binary = ''
  for (const byte of new TextEncoder().encode(String(text || ''))) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * The proxy's URL for `name`'s photo. `deezerUrl`, when the page already has
 * the artist's Deezer picture, is sent along (base64url-encoded) and relayed
 * instead of searching Deezer for the name - a saved photo still wins.
 */
export function proxiedArtistPhotoUrl(name, deezerUrl = '') {
  const text = String(name || '').trim()
  if (!text) return ''
  const base = `/api/artists/photo-proxy?name=${encodeURIComponent(text)}`
  return deezerUrl ? `${base}&url=${base64Url(deezerUrl)}` : base
}

/**
 * An artist's photo on a page that already has their Deezer picture
 * (Discover, the Finder), as the `{ cover, fallback }` a CoverArt takes: the
 * proxy - the saved photo when there is one, else that picture, with no
 * search by name - and the picture itself behind it, for when the proxy
 * can't answer. No picture: the proxy searches by name, as before.
 */
export function knownArtistPhoto(name, deezerUrl) {
  const url = String(deezerUrl || '')
  return { cover: proxiedArtistPhotoUrl(name, url), fallback: url }
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
