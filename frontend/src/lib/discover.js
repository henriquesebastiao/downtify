// Discover: what the page sends the server, and when a play counts as a
// listen. Pure, so it's unit-testable.

/** A track shorter than this never counts as a listen. */
export const LISTEN_MIN_DURATION = 30
/** Past this many seconds played, any track counts (Last.fm's own rule). */
export const LISTEN_MAX_SECONDS = 240
/** A jump in the playhead longer than this is a seek, not playback. */
const MAX_TICK = 3

/**
 * `POST /api/discover`'s `library`: every library artist (as the Library
 * page groups them) with how many of their tracks are in it and how many
 * of those are liked.
 */
export function libraryPayload(artists, liked = new Set()) {
  return (artists || [])
    .filter((artist) => artist?.name)
    .map((artist) => ({
      name: artist.name,
      tracks: artist.tracks.length,
      liked: artist.tracks.filter((track) => liked.has(track.file)).length,
    }))
}

/**
 * `POST /api/discover/collections`'s body: the library's artists (as for
 * `libraryPayload`), its albums - so one already downloaded isn't suggested
 * - and the Spotify ids of the playlists downloaded from Spotify.
 */
export function collectionsPayload(artists, albums, playlists, liked) {
  return {
    library: libraryPayload(artists, liked),
    albums: (albums || [])
      .filter((album) => album?.title)
      .map((album) => ({ artist: album.artist || '', title: album.title })),
    playlist_ids: (playlists || [])
      .map((playlist) => playlist?.batch?.spotify_playlist_id)
      .filter(Boolean),
  }
}

/**
 * The artist a play of `track` counts for - the same name the Library
 * groups it under - or `''` for what doesn't count (a podcast episode, or
 * anything that isn't a library file).
 */
export function listenArtist(track) {
  if (!track?.file || track.isPodcast) return ''
  return track.albumArtist || track.artists?.[0] || track.artist || ''
}

/** Seconds of a track that must actually play before it's a listen. */
export function listenThreshold(duration) {
  if (!(duration >= LISTEN_MIN_DURATION)) return Infinity
  return Math.min(duration / 2, LISTEN_MAX_SECONDS)
}

/**
 * Seconds actually played, given the playhead moved from `last` to `now`:
 * small forward steps add up, a seek (backwards or a big jump) doesn't.
 */
export function addPlayed(played, last, now) {
  const step = now - last
  return step > 0 && step <= MAX_TICK ? played + step : played
}

/** "A, B and C" in the page's language. */
export function joinNames(names, locale) {
  const list = (names || []).filter(Boolean)
  try {
    return new Intl.ListFormat(locale, {
      style: 'long',
      type: 'conjunction',
    }).format(list)
  } catch {
    return list.join(', ')
  }
}

/** A suggestion's page on Deezer, or `''`. */
export function deezerArtistUrl(item) {
  return item?.deezer_id
    ? `https://www.deezer.com/artist/${encodeURIComponent(item.deezer_id)}`
    : ''
}
