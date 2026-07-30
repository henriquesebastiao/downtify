// Spotify URLs copied while using the interface in a non-default language
// include a locale segment, e.g.:
//   https://open.spotify.com/intl-pt/album/2dZMT4gpOWtIYtvdSLT4pr?si=...
// Strip that segment so URL detection works regardless of locale.
export function normalizeSpotifyURL(str) {
  return (str || '').replace(
    /(open\.spotify\.com\/)intl-[a-zA-Z]{2,4}(?:-[a-zA-Z]{2,4})?\//,
    '$1'
  )
}
