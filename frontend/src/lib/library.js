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

function splitArtists(artist) {
  const text = String(artist || '').trim()
  if (!text) return []
  for (const sep of [';', ' / ', ', ']) {
    if (text.includes(sep)) {
      return text
        .split(sep)
        .map((part) => part.trim())
        .filter(Boolean)
    }
  }
  return [text]
}

const VARIOUS_ARTISTS = new Set(['various artists', 'various'])

function isVariousArtists(name) {
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
  const artists = splitArtists(artist)
  const albumArtist = groupingArtistName({
    albumArtist: String(raw.album_artist || '').trim(),
    artists,
    artist,
  })
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
    explicit: Boolean(raw.explicit),
    // Admins only: why users can't see this track ('track', 'album' or
    // 'artist' - the widest rule that hides it), '' when they can.
    hiddenBy: String(raw.hidden_by || ''),
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
 * Group tracks into albums by album artist + album title. Tracks with no
 * album tag aren't an album; they stay reachable from Tracks and Artists.
 */
export function groupAlbums(tracks) {
  const map = new Map()
  for (const track of tracks) {
    if (!track.album) continue
    const artist = groupingArtistName(track)
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
        hiddenBy: '',
      }
      map.set(key, album)
    }
    album.tracks.push(track)
    album.added = Math.max(album.added, track.added)
    album.duration += track.duration
    album.size += track.size
    // A rule on the album (or its artist) hides the whole album; one on a
    // single track doesn't.
    if (track.hiddenBy === 'artist') album.hiddenBy = 'artist'
    else if (track.hiddenBy === 'album' && !album.hiddenBy) {
      album.hiddenBy = 'album'
    }
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

/** Group tracks by (album) artist, with their albums attached. */
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
        hiddenBy: '',
      })
    }
    return map.get(key)
  }
  for (const track of tracks) {
    const name = groupingArtistName(track)
    if (!name) continue
    const artist = entry(name)
    artist.tracks.push(track)
    artist.added = Math.max(artist.added, track.added)
    artist.duration += track.duration
    if (track.hiddenBy === 'artist') artist.hiddenBy = 'artist'
    if (!artist.cover && track.hasCover) artist.cover = track.cover
  }
  for (const album of albums) {
    if (!album.artist) continue
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
      // A manual playlist uses a live mosaic unless a source image was
      // explicitly imported with it.
      cover:
        playlist.manual && !playlist.explicit_cover
          ? ''
          : playlistCoverURL(playlist.cover),
      covers,
      duration: tracks.reduce((sum, track) => sum + track.duration, 0),
      // M3U mtime from GET /playlists — not the resolved tracks, or the
      // sidebar would reshuffle every time a playlist's songs load.
      added: Number(playlist.added) || 0,
      batch: batchByName.get(playlist.name) || null,
      // Sharing (see downtify/playlist_shares.py). Without these fields a
      // playlist is the user's own and private.
      mine: playlist.mine !== false,
      canEditTracks: Boolean(playlist.can_edit_tracks),
      editors: Array.isArray(playlist.editors) ? playlist.editors : [],
      owner: String(playlist.owner || ''),
      visibility: playlist.visibility || 'private',
      sharedWith: Array.isArray(playlist.shared_with)
        ? playlist.shared_with
        : [],
      followed: Boolean(playlist.followed),
      sharedWithMe: Boolean(playlist.shared_with_me),
      isNew: Boolean(playlist.new),
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
      mine: true,
      owner: '',
      visibility: 'private',
      sharedWith: [],
      followed: false,
      sharedWithMe: false,
      isNew: false,
    }))
  return [...fromM3u, ...tracked]
}

/**
 * The playlists in the three places they are listed, never mixed: the
 * user's own, those shared with them by name (new ones first) and other
 * people's public ones (by owner, then name).
 */
export function splitPlaylists(playlists) {
  const own = []
  const shared = []
  const publicOnes = []
  for (const playlist of playlists) {
    if (playlist.mine) own.push(playlist)
    else if (playlist.sharedWithMe) shared.push(playlist)
    else publicOnes.push(playlist)
  }
  const byOwner = (a, b) =>
    compareText(a.owner, b.owner) ||
    compareText(a.title ?? a.name, b.title ?? b.name)
  shared.sort((a, b) => Number(b.isNew) - Number(a.isNew) || byOwner(a, b))
  publicOnes.sort(byOwner)
  return { own, shared, public: publicOnes }
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

/**
 * The orders a track list can be sorted in, as the sort picker offers
 * them: `[name, key, dir]` for `sortItems`. `order` is a playlist's own
 * order (not a sorter). Note that for `added` and `duration` the
 * library's "ascending" is newest / longest first, as the column
 * headers have always sorted.
 */
export const TRACK_SORTS = [
  ['order', 'order', 'asc'],
  ['addedNew', 'added', 'asc'],
  ['addedOld', 'added', 'desc'],
  ['titleAsc', 'title', 'asc'],
  ['titleDesc', 'title', 'desc'],
  ['artistAsc', 'artist', 'asc'],
  ['artistDesc', 'artist', 'desc'],
  ['albumAsc', 'album', 'asc'],
  ['albumDesc', 'album', 'desc'],
  ['longest', 'duration', 'asc'],
  ['shortest', 'duration', 'desc'],
]

/** The picker's name for a `{ key, dir }` sort, or '' when it has none. */
export function trackSortName(sort) {
  const found = TRACK_SORTS.find(
    ([, key, dir]) => key === sort?.key && dir === (sort?.dir || 'asc')
  )
  return found ? found[0] : ''
}

/** The `{ key, dir }` sort for a picker name (the default for an unknown one). */
export function trackSortByName(name) {
  const found = TRACK_SORTS.find(([id]) => id === name) || TRACK_SORTS[1]
  return { key: found[1], dir: found[2] }
}

/**
 * `tracks` in the order `sort` (`{ key, dir }`) says. `order` keeps the
 * list as it came, which for a playlist is the playlist's own order.
 */
export function sortTracks(tracks, sort) {
  if (!sort || sort.key === 'order') return tracks
  return sortItems(tracks, sort.key, sort.dir)
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
