// Reactive library store: tracks, albums, artists and playlists.
// Home loads a small summary. Other pages fetch only the slice they
// show; the full GET /tracks catalog is for the Library tracks tab.
import { computed, ref, shallowRef } from 'vue'

import API from '/src/model/api'
import {
  albumKey,
  artistKey,
  buildPlaylists,
  groupAlbums,
  groupArtists,
  normalizeTrack,
  indexTracksBySong,
  songKey,
} from '/src/lib/library'
import { coverURL } from '/src/lib/paths'
import { usePlayer } from '/src/model/player'
import { useI18n } from '/src/i18n'

const tracks = shallowRef([])
const albumsIndex = shallowRef([])
const artistsIndex = shallowRef([])
const rawPlaylists = shallowRef([])
const batches = shallowRef([])
const loading = ref(false)
const loaded = ref(false)
const tracksComplete = ref(false)
const albumsComplete = ref(false)
const artistsComplete = ref(false)
const error = ref('')
const summary = shallowRef({
  trackCount: 0,
  albumCount: 0,
  artistCount: 0,
  size: 0,
  recentAlbums: [],
})

const tracksByFile = computed(
  () => new Map(tracks.value.map((track) => [track.file, track]))
)
const albums = computed(() => {
  if (tracksComplete.value) return groupAlbums(tracks.value)
  if (albumsComplete.value) {
    const grouped = groupAlbums(tracks.value)
    const byKey = new Map(grouped.map((album) => [album.key, album]))
    return albumsIndex.value.map((album) => byKey.get(album.key) || album)
  }
  return summary.value.recentAlbums
})
const artists = computed(() => {
  if (tracksComplete.value) {
    return groupArtists(tracks.value, albums.value)
  }
  return artistsIndex.value
})
const { t } = useI18n()
const playlists = computed(() =>
  buildPlaylists(rawPlaylists.value, tracksByFile.value, batches.value).map(
    (playlist) =>
      playlist.liked ? { ...playlist, title: t('likes.playlist') } : playlist
  )
)
const totalSize = computed(() =>
  tracksComplete.value
    ? tracks.value.reduce((sum, track) => sum + track.size, 0)
    : summary.value.size
)
const trackCount = computed(() =>
  tracksComplete.value ? tracks.value.length : summary.value.trackCount
)
const albumCount = computed(() =>
  tracksComplete.value
    ? albums.value.length
    : albumsComplete.value
      ? albumsIndex.value.length
      : summary.value.albumCount
)
const artistCount = computed(() =>
  tracksComplete.value
    ? artists.value.length
    : artistsComplete.value
      ? artistsIndex.value.length
      : summary.value.artistCount
)
const songKeys = computed(
  () => new Set(tracks.value.map((track) => songKey(track.artist, track.title)))
)
const tracksBySong = computed(() => indexTracksBySong(tracks.value))

let pending = null
let pendingTracks = null
let pendingAlbums = null
let pendingArtists = null

function albumFromSummary(row) {
  const albumTracks = (row.tracks || []).map(normalizeTrack)
  const coverTrack = albumTracks.find((track) => track.hasCover)
  return {
    key: albumKey(row.artist, row.title),
    title: row.title,
    artist: row.artist,
    year: row.year || '',
    tracks: albumTracks,
    trackCount: albumTracks.length,
    cover: coverTrack ? coverURL(coverTrack.file) : '',
    added: Number(row.added) || 0,
    duration: albumTracks.reduce((sum, track) => sum + track.duration, 0),
    size: albumTracks.reduce((sum, track) => sum + track.size, 0),
  }
}

function albumFromIndex(row) {
  const coverFile = String(row.cover_file || '')
  return {
    key: albumKey(row.artist, row.title),
    title: row.title,
    artist: row.artist,
    year: row.year || '',
    tracks: [],
    trackCount: Number(row.track_count) || 0,
    cover: coverFile ? coverURL(coverFile) : '',
    added: Number(row.added) || 0,
    duration: Number(row.duration) || 0,
    size: Number(row.size) || 0,
  }
}

function artistFromIndex(row) {
  const coverFile = String(row.cover_file || '')
  return {
    key: artistKey(row.name),
    name: row.name,
    tracks: [],
    albums: [],
    trackCount: Number(row.track_count) || 0,
    albumCount: Number(row.album_count) || 0,
    likedCount: Number(row.liked_count) || 0,
    cover: coverFile ? coverURL(coverFile) : '',
    added: Number(row.added) || 0,
    duration: Number(row.duration) || 0,
  }
}

function applySummary(data) {
  const payload = data || {}
  summary.value = {
    trackCount: Number(payload.track_count) || 0,
    albumCount: Number(payload.album_count) || 0,
    artistCount: Number(payload.artist_count) || 0,
    size: Number(payload.size) || 0,
    recentAlbums: (payload.recent_albums || []).map(albumFromSummary),
  }
}

function mergeTrackRows(rows) {
  const incoming = (rows || []).map(normalizeTrack)
  if (!tracks.value.length) {
    tracks.value = incoming
    return
  }
  const map = new Map(tracks.value.map((track) => [track.file, track]))
  for (const track of incoming) map.set(track.file, track)
  tracks.value = [...map.values()]
}

async function load({ force = false } = {}) {
  if (pending) return pending
  if (loaded.value && !force) return undefined
  loading.value = true
  error.value = ''
  pending = (async () => {
    try {
      const [summaryRes, playlistsRes, batchesRes] = await Promise.all([
        API.getLibrarySummary(),
        API.listPlaylists(),
        API.getPlaylistBatches().catch(() => ({ data: { playlists: [] } })),
      ])
      applySummary(summaryRes.data)
      rawPlaylists.value = playlistsRes.data || []
      batches.value = batchesRes.data?.playlists || []
      loaded.value = true
      if (tracksComplete.value) await ensureTracks({ force: true })
      if (albumsComplete.value) await ensureAlbums({ force: true })
      if (artistsComplete.value) await ensureArtists({ force: true })
    } catch (err) {
      error.value = err?.message || 'failed'
    } finally {
      loading.value = false
      pending = null
    }
  })()
  return pending
}

async function ensureTracks({ force = false } = {}) {
  if (pendingTracks) return pendingTracks
  if (tracksComplete.value && !force) return undefined
  pendingTracks = (async () => {
    loading.value = true
    try {
      const res = await API.listTracks()
      tracks.value = (res.data || []).map(normalizeTrack)
      tracksComplete.value = true
      usePlayer().refreshTracks(tracksByFile.value)
    } finally {
      loading.value = false
    }
  })().finally(() => {
    pendingTracks = null
  })
  return pendingTracks
}

async function ensureAlbums({ force = false } = {}) {
  if (pendingAlbums) return pendingAlbums
  if (albumsComplete.value && !force) return undefined
  if (tracksComplete.value) {
    albumsComplete.value = true
    return undefined
  }
  pendingAlbums = (async () => {
    loading.value = true
    try {
      const res = await API.getLibraryAlbums()
      albumsIndex.value = (res.data || []).map(albumFromIndex)
      albumsComplete.value = true
    } finally {
      loading.value = false
    }
  })().finally(() => {
    pendingAlbums = null
  })
  return pendingAlbums
}

async function ensureArtists({ force = false } = {}) {
  if (pendingArtists) return pendingArtists
  if (artistsComplete.value && !force) return undefined
  if (tracksComplete.value) {
    artistsComplete.value = true
    return undefined
  }
  pendingArtists = (async () => {
    loading.value = true
    try {
      const res = await API.getLibraryArtists()
      artistsIndex.value = (res.data || []).map(artistFromIndex)
      artistsComplete.value = true
    } finally {
      loading.value = false
    }
  })().finally(() => {
    pendingArtists = null
  })
  return pendingArtists
}

async function loadPlaylistTracks(name) {
  const text = String(name || '').trim()
  if (!text) return
  const res = await API.listTracks({ playlist: text })
  mergeTrackRows(res.data)
  usePlayer().refreshTracks(tracksByFile.value)
}

async function loadArtistTracks(name) {
  const text = String(name || '').trim()
  if (!text) return
  const res = await API.listTracks({ artist: text })
  mergeTrackRows(res.data)
  usePlayer().refreshTracks(tracksByFile.value)
}

async function searchTracks(query, { limit = 80 } = {}) {
  const res = await API.listTracks({ q: query, limit })
  const rows = (res.data || []).map(normalizeTrack)
  mergeTrackRows(rows)
  usePlayer().refreshTracks(tracksByFile.value)
  return rows
}

async function lookupSongs(songs) {
  const list = (songs || []).filter(Boolean)
  if (!list.length) return []
  const res = await API.lookupLibrarySongs(list)
  mergeTrackRows(res.data)
  usePlayer().refreshTracks(tracksByFile.value)
  return res.data || []
}

let refreshTimer = null

/** Reload shortly — coalesces bursts of finished downloads. */
function refreshSoon(delay = 2500) {
  if (!loaded.value) return
  clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => load({ force: true }), delay)
}

API.onMessage((data) => {
  if (data?.status === 'done') refreshSoon()
})

function forget(files) {
  const gone = new Set(files)
  tracks.value = tracks.value.filter((track) => !gone.has(track.file))
  rawPlaylists.value = rawPlaylists.value.map((playlist) => ({
    ...playlist,
    files: (playlist.files || []).filter((file) => !gone.has(file)),
  }))
  usePlayer().forgetFiles(files)
  if (!tracksComplete.value) {
    if (albumsComplete.value) void ensureAlbums({ force: true })
    if (artistsComplete.value) void ensureArtists({ force: true })
  }
}

function forgetByPrefix(prefix) {
  const text = String(prefix || '')
  if (!text) return
  forget(
    tracks.value
      .filter((track) => String(track.file || '').startsWith(text))
      .map((track) => track.file)
  )
}

/** Delete tracks from disk; resolves `{ deleted, failed }`. */
async function deleteFiles(files) {
  const res = await API.deleteDownloadsBatch(files)
  const results = res.data?.results || {}
  const deleted = files.filter((file) => results[file]?.deleted)
  forget(deleted)
  return { deleted, failed: files.length - deleted.length }
}

async function deletePlaylist(playlist) {
  const sid = playlist.batch?.spotify_playlist_id
  const res = sid
    ? await API.deletePlaylistBatch(sid)
    : await API.deleteLibraryPlaylist(playlist.name)
  forget(res.data?.files || [])
  await load({ force: true })
  return res.data
}

/** Start a ZIP download of `files` in the browser. */
async function downloadZip(files) {
  const res = await API.prepareLibraryArchive(files)
  const token = res.data?.token
  if (!token) throw new Error('no token')
  window.location.assign(API.libraryArchiveURL(token))
  return res.data
}

function findAlbum(artist, title) {
  const key = albumKey(artist, title)
  const grouped = groupAlbums(tracks.value)
  const live = grouped.find((album) => album.key === key)
  if (live?.tracks.length) return live
  return albums.value.find((album) => album.key === key) || live || null
}

function findArtist(name) {
  const key = artistKey(name)
  const grouped = groupArtists(tracks.value)
  const live = grouped.find((artist) => artist.key === key)
  if (live?.tracks.length) return live
  return artists.value.find((artist) => artist.key === key) || live || null
}

function findPlaylist(name) {
  return playlists.value.find((playlist) => playlist.name === name) || null
}

function hasSong(artist, title) {
  return songKeys.value.has(songKey(artist, title))
}

/** The library track for a song that is already downloaded, or `null`. */
function findTrack(artist, title) {
  return tracksBySong.value.get(songKey(artist, title)) || null
}

export function useLibrary() {
  return {
    tracks,
    albums,
    artists,
    playlists,
    batches,
    tracksByFile,
    totalSize,
    trackCount,
    albumCount,
    artistCount,
    loading,
    loaded,
    tracksComplete,
    albumsComplete,
    artistsComplete,
    error,
    load,
    ensureTracks,
    ensureAlbums,
    ensureArtists,
    loadPlaylistTracks,
    loadArtistTracks,
    searchTracks,
    lookupSongs,
    refreshSoon,
    forget,
    forgetByPrefix,
    deleteFiles,
    deletePlaylist,
    downloadZip,
    findAlbum,
    findArtist,
    findPlaylist,
    hasSong,
    findTrack,
  }
}
