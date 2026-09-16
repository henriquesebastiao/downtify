// Reactive library store: tracks, albums, artists and playlists built
// from GET /tracks, GET /playlists and the playlist download tracking.
import { computed, ref, shallowRef } from 'vue'

import API from '/src/model/api'
import {
  albumKey,
  artistKey,
  buildPlaylists,
  groupAlbums,
  groupArtists,
  normalizeTrack,
  songKey,
} from '/src/lib/library'
import { usePlayer } from '/src/model/player'

const tracks = shallowRef([])
const rawPlaylists = shallowRef([])
const batches = shallowRef([])
const loading = ref(false)
const loaded = ref(false)
const error = ref('')

const tracksByFile = computed(
  () => new Map(tracks.value.map((track) => [track.file, track]))
)
const albums = computed(() => groupAlbums(tracks.value))
const artists = computed(() => groupArtists(tracks.value, albums.value))
const playlists = computed(() =>
  buildPlaylists(rawPlaylists.value, tracksByFile.value, batches.value)
)
const totalSize = computed(() =>
  tracks.value.reduce((sum, track) => sum + track.size, 0)
)
// "Is this song already downloaded?" lookups for search/link results.
const songKeys = computed(
  () => new Set(tracks.value.map((track) => songKey(track.artist, track.title)))
)

let pending = null

async function load({ force = false } = {}) {
  if (pending) return pending
  if (loaded.value && !force) return undefined
  loading.value = true
  error.value = ''
  pending = (async () => {
    try {
      const [tracksRes, playlistsRes, batchesRes] = await Promise.all([
        API.listTracks(),
        API.listPlaylists(),
        API.getPlaylistBatches().catch(() => ({ data: { playlists: [] } })),
      ])
      tracks.value = (tracksRes.data || []).map(normalizeTrack)
      rawPlaylists.value = playlistsRes.data || []
      batches.value = batchesRes.data?.playlists || []
      loaded.value = true
      usePlayer().refreshTracks(tracksByFile.value)
    } catch (err) {
      error.value = err?.message || 'failed'
    } finally {
      loading.value = false
      pending = null
    }
  })()
  return pending
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
  return albums.value.find((album) => album.key === key) || null
}

function findArtist(name) {
  const key = artistKey(name)
  return artists.value.find((artist) => artist.key === key) || null
}

function findPlaylist(name) {
  return playlists.value.find((playlist) => playlist.name === name) || null
}

function hasSong(artist, title) {
  return songKeys.value.has(songKey(artist, title))
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
    loading,
    loaded,
    error,
    load,
    refreshSoon,
    deleteFiles,
    deletePlaylist,
    downloadZip,
    findAlbum,
    findArtist,
    findPlaylist,
    hasSong,
  }
}
