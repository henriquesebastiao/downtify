// DISPLAY-ONLY photos for artists that have no saved photo: the related
// artists of the artist page, the Library's artists grid and the artist
// page's own round photo.
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

export function proxiedArtistPhotoUrl(name) {
  const text = String(name || '').trim()
  if (!text) return ''
  return `/api/artists/photo-proxy?name=${encodeURIComponent(text)}`
}
