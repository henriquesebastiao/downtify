// Turns the flat `GET /tracks` rows into the Library's tracks, albums
// and artists. Pure functions — the reactive store lives in
// model/library.js.

import { coverURL, fileURL, playlistCoverURL } from './paths'
import { fileFormat } from './format'

const collator = new Intl.Collator(undefined, {
  sensitivity: 'base',
  numeric: true,
})

export function compareText(a, b) {
  return collator.compare(String(a || ''), String(b || ''))
}

// What sits between the members' names in an act's own name: "Henrique &
// Juliano", "Simon + Garfunkel", "Sandy e Junior", "Zé Neto, Cristiano".
const ACT_NAME_JOINER = String.raw`\s*(?:&|\+|,|/|\b(?:e|and|y|x)\b)\s*`

/** Whether `act` is the name of an act made of exactly `names` (two or
 * more), joined the way an act's name joins its members, in any order.
 * Mirrors is_act_of in downtify/album_artist.py. */
export function isActOf(names, act) {
  if (names.length < 2) return false
  const members = String(act || '')
    .toLowerCase()
    .split(new RegExp(ACT_NAME_JOINER))
    .map((part) => part.trim())
    .filter(Boolean)
    .sort()
  const wanted = names.map((name) => String(name).trim().toLowerCase()).sort()
  return (
    members.length === wanted.length &&
    members.every((part, i) => part === wanted[i])
  )
}

// The artists in an artist tag's text, when the server sent no list (a
// file without an ARTISTS tag). A text that is the album artist too is one
// name - "Earth, Wind & Fire" on its own album - and isn't split; so is a
// split whose names make up the album artist ("Henrique; Juliano" on an
// album by "Henrique, Juliano": an act YouTube Music credited as its
// members). Mirrors split_artists in downtify/library_metadata.py.
function splitArtists(artist, albumArtist = '') {
  const text = String(artist || '').trim()
  if (!text) return []
  const owner = String(albumArtist || '').trim()
  if (text.toLowerCase() === owner.toLowerCase()) return [text]
  for (const sep of [';', ' / ', ', ']) {
    if (text.includes(sep)) {
      const parts = text
        .split(sep)
        .map((part) => part.trim())
        .filter(Boolean)
      return isActOf(parts, owner) ? [owner] : parts
    }
  }
  return [text]
}

const VARIOUS_ARTISTS = new Set(['various artists', 'various'])

/** Whether an album artist is the "Various Artists" of a compilation
 * (see downtify/album_artist.py). */
export function isVariousArtists(name) {
  return VARIOUS_ARTISTS.has(
    String(name || '')
      .trim()
      .toLowerCase()
  )
}

/** Album artist the Library groups under — skips a compilation tag. */
export function groupingArtistName(track) {
  const tagged = String(track?.albumArtist || '').trim()
  if (tagged && !isVariousArtists(tagged)) return tagged
  const first = String(track?.artists?.[0] || '').trim()
  if (first && !isVariousArtists(first)) return first
  return String(track?.artist || '')
    .split(';')[0]
    .trim()
}

function basenameTitle(file) {
  const base = String(file || '')
    .split('/')
    .pop()
    .replace(/\.[^.]+$/, '')
  const dash = base.indexOf(' - ')
  if (dash <= 0) return { artist: '', title: base }
  return {
    artist: base.slice(0, dash).trim(),
    title: base.slice(dash + 3).trim(),
  }
}

/** A `/tracks` row (or a bare path) as the track object the UI uses. */
export function normalizeTrack(row) {
  const raw = typeof row === 'string' ? { file: row } : row || {}
  const file = String(raw.file || '')
  const fallback = basenameTitle(file)
  const artist = String(raw.artist || '').trim() || fallback.artist
  // Every credited artist: the server reads them one by one from the
  // file's ARTISTS tag when it has one; only then is the text split here.
  const listed = Array.isArray(raw.artists)
    ? raw.artists.map((name) => String(name || '').trim()).filter(Boolean)
    : []
  const artists = listed.length
    ? listed
    : splitArtists(artist, raw.album_artist)
  const albumArtist = String(raw.album_artist || '').trim() || artists[0] || ''
  return {
    file,
    title: String(raw.title || '').trim() || fallback.title,
    artist,
    artists,
    album: String(raw.album || '').trim(),
    albumArtist,
    trackNumber: Number(raw.track_number) || 0,
    year: String(raw.year || ''),
    duration: Number(raw.duration) || 0,
    added: Number(raw.added) || 0,
    size: Number(raw.size) || 0,
    // Bare paths (no /tracks row) don't know; try the cover endpoint.
    hasCover: raw.has_cover !== false,
    playlists: Array.isArray(raw.playlists) ? raw.playlists : [],
    format: fileFormat(file),
    url: fileURL(file),
    cover: coverURL(file),
  }
}

export function albumKey(albumArtist, album) {
  return JSON.stringify([
    String(albumArtist || '').toLowerCase(),
    String(album || '').toLowerCase(),
  ])
}

function byTrackOrder(a, b) {
  return (
    (a.trackNumber || 9999) - (b.trackNumber || 9999) ||
    compareText(a.title, b.title)
  )
}

/**
 * Group tracks into albums by album artist + album title - the album
 * artist tag as it is, so a compilation ("Various Artists") stays one
 * album; its tracks are on their own artists' pages (groupArtists).
 * Tracks with no album tag aren't an album; they stay reachable from
 * Tracks and Artists.
 */
export function groupAlbums(tracks) {
  const map = new Map()
  for (const track of tracks) {
    if (!track.album) continue
    const artist = track.albumArtist
    const key = albumKey(artist, track.album)
    let album = map.get(key)
    if (!album) {
      album = {
        key,
        title: track.album,
        artist,
        year: '',
        tracks: [],
        cover: '',
        added: 0,
        duration: 0,
        size: 0,
      }
      map.set(key, album)
    }
    album.tracks.push(track)
    album.added = Math.max(album.added, track.added)
    album.duration += track.duration
    album.size += track.size
    if (!album.year && track.year) album.year = track.year
    if (!album.cover && track.hasCover) album.cover = track.cover
  }
  const albums = [...map.values()]
  for (const album of albums) album.tracks.sort(byTrackOrder)
  return albums
}

export function artistKey(name) {
  return String(name || '').toLowerCase()
}

/**
 * Whether `track` is only a guest appearance for `name`: they're credited
 * on it, but it belongs to another artist (see groupingArtistName).
 */
export function isGuestOn(track, name) {
  return artistKey(groupingArtistName(track)) !== artistKey(name)
}

/**
 * A track's credited artists as `{ name, to }` for a line of artist links:
 * `to` is the artist's Library page, or `null` for plain text. Every name
 * links to its page, unless `plain`; with `hasPage`, only the names it
 * says have one (a song not in the Library yet) - and with `searchMissing`
 * the others link to a search for them instead. No artists: just
 * `fallback`, never a link.
 */
export function artistLinkItems(
  artists,
  { fallback = '', plain = false, hasPage = null, searchMissing = false } = {}
) {
  const names = (artists || [])
    .map((name) => String(name || '').trim())
    .filter(Boolean)
  if (!names.length) return fallback ? [{ name: fallback, to: null }] : []
  return names.map((name) => {
    if (plain) return { name, to: null }
    if (!hasPage || hasPage(name)) {
      return { name, to: { name: 'Artist', query: { name } } }
    }
    return {
      name,
      to: searchMissing ? { name: 'Search', params: { query: name } } : null,
    }
  })
}

/**
 * Where a song's album name links: the album's Library page when the
 * Library has it - same title (ignoring case and accents), by the song's
 * album artist or one of its artists, or a compilation of that title -
 * else a search for the album, unless `search` is off (then `null`).
 * `null` when the song names no album.
 */
export function albumLinkFor(albums, song, { search = true } = {}) {
  const title = String(song?.album_name || '').trim()
  if (!title) return null
  const artists = [song?.album_artist, ...(song?.artists || [])]
    .map((name) => fold(String(name || '').trim()))
    .filter(Boolean)
  const sameTitle = (albums || []).filter(
    (album) => fold(album.title) === fold(title)
  )
  const found =
    sameTitle.find((album) => artists.includes(fold(album.artist))) ||
    sameTitle.find((album) => isVariousArtists(album.artist))
  if (found) {
    return {
      name: 'Album',
      query: { artist: found.artist, title: found.title },
    }
  }
  if (!search) return null
  const artist = (song?.artists || [])[0] || song?.album_artist || ''
  return {
    name: 'Search',
    params: { query: [artist, title].filter(Boolean).join(' ') },
  }
}

/**
 * Group tracks by artist, with their albums attached. A track counts for
 * the artist it belongs to (groupingArtistName) and for every other artist
 * credited on it, so a guest gets a page of their own; albums only count
 * for their album artist. "Various Artists" is never one of them.
 */
export function groupArtists(tracks, albums = groupAlbums(tracks)) {
  const map = new Map()
  const entry = (name) => {
    const key = artistKey(name)
    if (!map.has(key)) {
      map.set(key, {
        key,
        name,
        tracks: [],
        albums: [],
        cover: '',
        added: 0,
        duration: 0,
      })
    }
    return map.get(key)
  }
  for (const track of tracks) {
    const names = new Map()
    for (const name of [groupingArtistName(track), ...track.artists]) {
      if (!name || isVariousArtists(name)) continue
      if (!names.has(artistKey(name))) names.set(artistKey(name), name)
    }
    for (const name of names.values()) {
      const artist = entry(name)
      artist.tracks.push(track)
      artist.added = Math.max(artist.added, track.added)
      artist.duration += track.duration
      if (!artist.cover && track.hasCover) artist.cover = track.cover
    }
  }
  for (const album of albums) {
    if (!album.artist || isVariousArtists(album.artist)) continue
    entry(album.artist).albums.push(album)
  }
  const artists = [...map.values()]
  for (const artist of artists) {
    artist.albums.sort(
      (a, b) => compareText(b.year, a.year) || compareText(a.title, b.title)
    )
  }
  return artists
}

/**
 * Downloaded playlists (`GET /playlists`, one per M3U) joined with the
 * library tracks they reference and, when known, their Spotify
 * download tracking (`GET /api/playlists/batches`).
 */
export function buildPlaylists(playlists, tracksByFile, batches = []) {
  const batchByName = new Map(
    batches.map((batch) => [String(batch.playlist_name || ''), batch])
  )
  const names = new Set(playlists.map((playlist) => playlist.name))
  const fromM3u = playlists.map((playlist) => {
    const files = playlist.files || []
    const tracks = files.map((file) => tracksByFile.get(file)).filter(Boolean)
    // Mosaic from the M3U paths so the sidebar does not wait for
    // GET /tracks rows. `/cover?file=` reads tags on its own.
    const covers = [...new Set(files.map((file) => coverURL(file)))].slice(0, 4)
    return {
      key: playlist.name.toLowerCase(),
      name: playlist.name,
      // What to show. The file on disk has a fixed name, so the liked
      // songs playlist is given a translated title by the model.
      title: playlist.name,
      // The playlist of hearted songs, not a downloaded one.
      liked: Boolean(playlist.liked),
      manual: Boolean(playlist.manual),
      fileCount: playlist.count != null ? Number(playlist.count) : files.length,
      tracks,
      // Downloaded playlists keep their own artwork. Manual ones leave
      // this empty so CoverArt mosaics up to four track covers (the
      // sidecar JPEG is still written for Navidrome).
      cover: playlist.manual ? '' : playlistCoverURL(playlist.cover),
      covers,
      duration: tracks.reduce((sum, track) => sum + track.duration, 0),
      // M3U mtime from GET /playlists — not the resolved tracks, or the
      // sidebar would reshuffle every time a playlist's songs load.
      added: Number(playlist.added) || 0,
      batch: batchByName.get(playlist.name) || null,
    }
  })
  // A tracked Spotify playlist whose M3U isn't written (M3U export off,
  // or nothing downloaded yet) still belongs in the list.
  const tracked = batches
    .filter((batch) => !names.has(String(batch.playlist_name || '')))
    .map((batch) => ({
      key: String(batch.playlist_name || '').toLowerCase(),
      name: String(batch.playlist_name || ''),
      title: String(batch.playlist_name || ''),
      liked: false,
      manual: false,
      fileCount: 0,
      tracks: [],
      cover: '',
      covers: [],
      duration: 0,
      added: 0,
      batch,
    }))
  return [...fromM3u, ...tracked]
}

const SORTERS = {
  added: (a, b) => b.added - a.added,
  title: (a, b) => compareText(a.title ?? a.name, b.title ?? b.name),
  artist: (a, b) =>
    compareText(a.artist, b.artist) ||
    compareText(a.title ?? a.name, b.title ?? b.name),
  album: (a, b) => compareText(a.album, b.album) || byTrackOrder(a, b),
  year: (a, b) => compareText(b.year, a.year) || compareText(a.title, b.title),
  duration: (a, b) => b.duration - a.duration,
  count: (a, b) => itemTrackCount(b) - itemTrackCount(a),
}

export const SORT_KEYS = Object.keys(SORTERS)

/** Track count for a grouped album/artist/playlist, or an index row. */
export function itemTrackCount(item) {
  // Playlists always know how many files the M3U lists. Prefer that over
  // `tracks.length`, which is only the songs already fetched.
  if (item != null && Number.isFinite(Number(item.fileCount))) {
    return Number(item.fileCount)
  }
  if (Array.isArray(item?.tracks) && item.tracks.length) {
    return item.tracks.length
  }
  return Number(item?.trackCount || 0)
}

export function sortItems(items, key, direction = 'asc') {
  const sorter = SORTERS[key] || SORTERS.added
  const sorted = [...items].sort(sorter)
  return direction === 'desc' ? sorted.reverse() : sorted
}

export function fold(text) {
  return String(text || '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

/**
 * Case- and accent-insensitive "every word matches somewhere" filter
 * over the given fields of each item.
 */
export function filterItems(items, query, fields) {
  const words = fold(query).split(/\s+/).filter(Boolean)
  if (!words.length) return items
  return items.filter((item) => {
    const haystack = fold(fields.map((field) => item[field]).join(' '))
    return words.every((word) => haystack.includes(word))
  })
}

/** Loose "is this song already downloaded?" key: artist + title. */
// Bracketed tags that don't make a different recording: guests and
// remasters. Mixes, live and acoustic versions stay distinct.
const SAME_SONG_TAG = /[([](?:(?:feat|ft|with)\b|[^)\]]*remaster)[^)\]]*[)\]]/g

export function songKey(artist, title) {
  const clean = (text) =>
    fold(text)
      .replace(SAME_SONG_TAG, ' ')
      .replace(/\s(feat|ft)\.?\s.*$/, ' ')
      .replace(/\s-\s[^-]*remaster[^-]*$/, ' ')
      .replace(/[^\p{L}\p{N}]+/gu, ' ')
      .trim()
  const first = String(artist || '')
    .split(/,|;| & /)[0]
    .trim()
  return `${clean(first)}|${clean(title)}`
}

/**
 * `songKey` -> library track, for finding the file behind a song that is
 * already downloaded (search and link results are songs, not files). The
 * first track wins when two share a key.
 */
export function indexTracksBySong(tracks) {
  const index = new Map()
  for (const track of tracks || []) {
    const key = songKey(track.artist, track.title)
    if (!index.has(key)) index.set(key, track)
  }
  return index
}
