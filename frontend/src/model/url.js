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

// A YouTube Music / YouTube playlist link, e.g.
//   https://music.youtube.com/playlist?list=PLx6XKQDAhfWZ4vxtvdmpkDKUnR2omdAdr&si=...
// Same rules as the backend's providers.parse_youtube_url: an album's
// OLAK5uy_ audio playlist is an album, an RD... radio mix has no fixed
// track list, and a watch?v= link is the song playing inside a playlist.
export function isYouTubePlaylistURL(str) {
  const url = str || ''
  if (!/(?:youtube\.com|youtu\.be)\//.test(url)) return false
  if (/\/browse\/VL[\w-]+/.test(url)) return true
  if (/[?&]v=/.test(url) || url.includes('youtu.be/')) return false
  const match = url.match(/[?&]list=([\w-]+)/)
  if (!match) return false
  const id = match[1]
  if (id.startsWith('OLAK5uy_')) return false
  return !(id.startsWith('RD') && !id.startsWith('RDCLAK5uy_'))
}
