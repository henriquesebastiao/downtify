// Discover: what the page sends the server, and when a play counts as a
// listen. Pure, so it's unit-testable.

import { groupingArtistName } from './library'

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
    .map((artist) => {
      const tracks = artist.tracks || []
      return {
        name: artist.name,
        tracks: tracks.length || Number(artist.trackCount) || 0,
        liked: tracks.length
          ? tracks.filter((track) => liked.has(track.file)).length
          : Number(artist.likedCount) || 0,
      }
    })
}

/**
 * The body of `POST /api/discover/collections/deezer` and `.../spotify`:
 * the library's artists (as for `libraryPayload`), its albums - so one
 * already downloaded isn't suggested - the Spotify ids of the playlists
 * downloaded from Spotify, and every library playlist's name (a downloaded
 * Deezer playlist is only known by it).
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
    playlist_names: (playlists || [])
      .map((playlist) => playlist?.name)
      .filter(Boolean),
  }
}

// Whatever tells two suggestions apart as the same album or playlist.
function identities(item) {
  return [
    item?.key && `key:${item.key}`,
    item?.deezer_album_id && `deezer:${item.deezer_album_id}`,
    item?.url && `url:${item.url}`,
  ].filter(Boolean)
}

/**
 * `incoming` added at the end of `list`, leaving out any it already has -
 * the same album (`key`, or Deezer id) or the same link. What's there never
 * moves, so nothing jumps while more suggestions arrive.
 */
export function appendNew(list, incoming) {
  const seen = new Set((list || []).flatMap(identities))
  const added = []
  for (const item of incoming || []) {
    const ids = identities(item)
    if (ids.some((id) => seen.has(id))) continue
    ids.forEach((id) => seen.add(id))
    added.push(item)
  }
  return added.length ? [...(list || []), ...added] : list || []
}

/**
 * Where a suggested album or playlist opens: a Deezer album in the Finder's
 * columns, anything else - a Spotify album, any playlist - on the Link page.
 */
export function collectionRoute(item) {
  if (
    item?.source === 'deezer' &&
    item.deezer_album_id &&
    item.deezer_artist_id
  ) {
    return {
      name: 'FinderBrowse',
      query: { artist: item.deezer_artist_id, album: item.deezer_album_id },
    }
  }
  return { name: 'Link', query: { url: item?.url || '' } }
}

/** Where a suggested artist's photo opens: the Finder, when Deezer knows it. */
export function artistRoute(item) {
  return item?.deezer_id
    ? { name: 'FinderBrowse', query: { artist: String(item.deezer_id) } }
    : { name: 'Search', params: { query: item?.name || '' } }
}

/**
 * The artist a play of `track` counts for - the same name the Library
 * groups it under - or `''` for what doesn't count (a podcast episode, or
 * anything that isn't a library file).
 */
export function listenArtist(track) {
  if (!track?.file || track.isPodcast) return ''
  return groupingArtistName(track)
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

/**
 * Where "Find songs" on a suggested artist goes: their songs in the Finder
 * (by their Deezer id), or - no id - a Finder search for their name.
 */
export function findSongsLocation(item) {
  const name = String(item?.name || '')
  return item?.deezer_id
    ? { name: 'Discover', query: { artist: String(item.deezer_id), name } }
    : { name: 'Discover', query: { q: name } }
}
