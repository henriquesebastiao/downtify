// DISPLAY-ONLY photos for artists that are not in the library.
//
// The URL below is served by the backend's photo proxy, which relays
// Deezer's picture and forgets it (the browser caches it for three hours).
// Use it for an <img> on screen and nowhere else: never save, upload or
// copy what it returns into an artist's photo/banner, and never call it
// for an artist that already has a saved photo — that one comes from
// `getArtistArt`/`getArtistArtBulk`. Pure (no API client import), like
// paths.js.

export function proxiedArtistPhotoUrl(name) {
  const text = String(name || '').trim()
  if (!text) return ''
  return `/api/artists/photo-proxy?name=${encodeURIComponent(text)}`
}
