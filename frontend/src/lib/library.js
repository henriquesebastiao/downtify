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
  return {
    file,
    title: String(raw.title || '').trim() || fallback.title,
    artist,
    artists,
    album: String(raw.album || '').trim(),
    albumArtist: String(raw.album_artist || '').trim() || artists[0] || '',
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
 * Group tracks into albums by album artist + album title. Tracks with no
 * album tag aren't an album; they stay reachable from Tracks and Artists.
 */
export function groupAlbums(tracks) {
  const map = new Map()
  for (const track of tracks) {
    if (!track.album) continue
    const key = albumKey(track.albumArtist, track.album)
    let album = map.get(key)
    if (!album) {
      album = {
        key,
        title: track.album,
        artist: track.albumArtist,
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
      })
    }
    return map.get(key)
  }
  for (const track of tracks) {
    const name = track.albumArtist || track.artists[0]
    if (!name) continue
    const artist = entry(name)
    artist.tracks.push(track)
    artist.added = Math.max(artist.added, track.added)
    artist.duration += track.duration
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
    const tracks = (playlist.files || [])
      .map((file) => tracksByFile.get(file))
      .filter(Boolean)
    const covers = [
      ...new Set(
        tracks.filter((track) => track.hasCover).map((track) => track.cover)
      ),
    ].slice(0, 4)
    return {
      key: playlist.name.toLowerCase(),
      name: playlist.name,
      // What to show. The file on disk has a fixed name, so the liked
      // songs playlist is given a translated title by the model.
      title: playlist.name,
      // The playlist of hearted songs, not a downloaded one.
      liked: Boolean(playlist.liked),
      tracks,
      // The playlist's own artwork, when it was downloaded; the grid of
      // track covers is only the fallback for playlists without one.
      cover: playlistCoverURL(playlist.cover),
      covers,
      duration: tracks.reduce((sum, track) => sum + track.duration, 0),
      added: tracks.reduce((max, track) => Math.max(max, track.added), 0),
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
  count: (a, b) => b.tracks.length - a.tracks.length,
}

export const SORT_KEYS = Object.keys(SORTERS)

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
