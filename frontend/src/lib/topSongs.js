// How an artist's top songs are sent to the download queue. Pure, so it's
// unit-testable.

/**
 * A playlist name as it ends up on disk. Mirrors `m3u.sanitize_playlist_name`
 * in the backend: characters that are illegal in file names go, whitespace
 * collapses, and leading/trailing dots and spaces are trimmed.
 */
export function sanitizePlaylistName(name) {
  const cleaned = String(name || '')
    .replace(/[\\/:*?"<>|\x00-\x1f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^\.+|\.+$/g, '')
    .trim()
  return cleaned || 'playlist'
}

/** The name the library lists an artist's top-songs playlist under. */
export function topSongsPlaylistName(artist) {
  return sanitizePlaylistName(`Top Songs of ${artist.name}`)
}

/**
 * The batch options for `fromSongs`. With "Create playlist" on the songs
 * become a playlist named after the artist, with an M3U and the artist's
 * photo as its cover. With it off they are plain downloads: no playlist
 * name (so no folder of their own), no M3U and no cover.
 */
export function topSongsBatchOptions(artist, createPlaylist) {
  if (!createPlaylist) return { playlistName: '', coverUrl: '', m3u: false }
  return {
    playlistName: `Top Songs of ${artist.name}`,
    coverUrl: artist.cover_url || '',
    m3u: true,
  }
}
