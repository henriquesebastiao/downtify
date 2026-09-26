// Discover: suggested artists, the block list, and counting listens.
//
// Suggestions are built on the server from the library (sent up, as the
// Library page groups it), the likes and the listens the player reports
// here - see downtify/discover.py. Listens are kept on the server, so what
// is played on a phone counts on the desktop too.
import { ref, shallowRef, watch } from 'vue'

import API from '/src/model/api'
import { usePlayer } from '/src/model/player'
import { addPlayed, listenArtist, listenThreshold } from '/src/lib/discover'
import { artistKey } from '/src/lib/library'

const items = shallowRef([])
const seeds = shallowRef([])
const partial = ref(false)
const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const blocked = shallowRef([])
// Albums and playlists built on the artists (POST /api/discover/collections):
// slower (a Spotify search per artist), so they load after the artists.
const albums = shallowRef([])
const moreAlbums = shallowRef([])
const playlists = shallowRef([])
// Spotify artist page per suggested artist, when the search found one.
const artistUrls = shallowRef({})
const collectionsLoading = ref(false)
const collectionsError = ref('')

let pending = null
let pendingCollections = null

/** Ask for suggestions; `library` is `libraryPayload(...)`. */
async function load(library) {
  if (pending) return pending
  loading.value = true
  error.value = ''
  pending = (async () => {
    try {
      const res = await API.getDiscover(library)
      items.value = res.data?.artists || []
      seeds.value = res.data?.seeds || []
      partial.value = Boolean(res.data?.partial)
      loaded.value = true
    } catch (err) {
      error.value = err?.response?.data?.detail || err?.message || 'failed'
    } finally {
      loading.value = false
      pending = null
    }
  })()
  return pending
}

/**
 * Albums and playlists; `payload` is `{ library, albums, playlist_ids }`
 * (see lib/discover.js `collectionsPayload`).
 */
async function loadCollections(payload) {
  if (pendingCollections) return pendingCollections
  collectionsLoading.value = true
  collectionsError.value = ''
  pendingCollections = (async () => {
    try {
      const res = await API.getDiscoverCollections(payload)
      albums.value = res.data?.albums || []
      moreAlbums.value = res.data?.more_albums || []
      playlists.value = res.data?.playlists || []
      artistUrls.value = res.data?.artist_urls || {}
      if (res.data?.partial) partial.value = true
    } catch (err) {
      collectionsError.value =
        err?.response?.data?.detail || err?.message || 'failed'
    } finally {
      collectionsLoading.value = false
      pendingCollections = null
    }
  })()
  return pendingCollections
}

async function loadBlocked() {
  try {
    const res = await API.getBlockedArtists()
    blocked.value = res.data || []
  } catch {
    // Keep what is shown; opening the list again retries.
  }
}

/** Never suggest `name` again. Hides it at once, undone if that fails. */
async function block(name) {
  const key = artistKey(name)
  const before = [items.value, albums.value, playlists.value]
  items.value = before[0].filter((item) => artistKey(item.name) !== key)
  // Their album and "This Is" playlist go with them.
  albums.value = before[1].filter((item) => artistKey(item.artist) !== key)
  playlists.value = before[2].filter(
    (item) => item.reason !== 'this_is' || artistKey(item.artist) !== key
  )
  try {
    const res = await API.blockArtist(name)
    blocked.value = [
      res.data,
      ...blocked.value.filter((row) => artistKey(row.name) !== key),
    ]
    return true
  } catch {
    ;[items.value, albums.value, playlists.value] = before
    return false
  }
}

async function unblock(name) {
  const key = artistKey(name)
  try {
    await API.unblockArtist(name)
    blocked.value = blocked.value.filter((row) => artistKey(row.name) !== key)
    return true
  } catch {
    return false
  }
}

async function clearListens() {
  try {
    await API.clearListens()
    return true
  } catch {
    return false
  }
}

// ── Listens: a library track counts once per play, after half of it (or
// four minutes) has actually played - seeking past the middle doesn't.
let tracking = false

function startListenTracking() {
  if (tracking) return
  tracking = true
  const player = usePlayer()
  let played = 0
  let last = 0
  let counted = false

  watch(player.currentTrack, () => {
    played = 0
    last = player.currentTime.value || 0
    counted = false
  })

  watch(player.currentTime, (now) => {
    played = addPlayed(played, last, now)
    // Back to the start (repeat one, or "previous" on the same song)
    // is a new play.
    if (counted && now < 1 && last > now) {
      played = 0
      counted = false
    }
    last = now
    const track = player.currentTrack.value
    const artist = listenArtist(track)
    if (counted || !artist) return
    if (played < listenThreshold(player.duration.value || track.duration))
      return
    counted = true
    API.recordListen(artist).catch(() => {
      // Best effort: one listen more or less barely moves the ranking.
    })
  })
}

export function useDiscover() {
  return {
    items,
    seeds,
    partial,
    loading,
    loaded,
    error,
    blocked,
    albums,
    moreAlbums,
    playlists,
    artistUrls,
    collectionsLoading,
    collectionsError,
    load,
    loadCollections,
    loadBlocked,
    block,
    unblock,
    clearListens,
    startListenTracking,
  }
}
