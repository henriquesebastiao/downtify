import { ref } from 'vue'

import API from '/src/model/api'

/** Route param when browsing a resolved Spotify playlist on the Search page. */
export const PLAYLIST_ROUTE_QUERY = '__spotify_playlist__'
export const PLAYLIST_URL_KEY = 'downtify-spotify-playlist-url'

const searchTerm = ref('')
const results = ref()
const isSearching = ref(false)
const error = ref(false)
const errorValue = ref('')
const browseKind = ref('text') // 'text' | 'spotify_playlist'
const playlistUrl = ref('')
const playlistTitle = ref('')

/** Decode route params and normalize pasted URLs. */
function normalizeInput(str) {
  let text = String(str || '').trim()
  if (!text || text === PLAYLIST_ROUTE_QUERY) return text
  try {
    if (/%[0-9A-Fa-f]{2}/.test(text)) {
      text = decodeURIComponent(text)
    }
  } catch {
    // keep raw
  }
  return text.trim()
}

function isSpotifyPlaylistURL(str) {
  const q = normalizeInput(str)
  return /open\.spotify\.com\/(?:intl-[^/]+\/)?playlist\//i.test(q)
}

function isSpotifyDirectDownloadURL(str) {
  const q = normalizeInput(str)
  return (
    /open\.spotify\.com\/(?:intl-[^/]+\/)?track\//i.test(q) ||
    /open\.spotify\.com\/(?:intl-[^/]+\/)?album\//i.test(q)
  )
}

function isAnySpotifyURL(str) {
  const q = normalizeInput(str)
  return /open\.spotify\.com\/(?:intl-[^/]+\/)?(track|album|playlist|artist)\//i.test(
    q
  )
}

function enrichSpotifyTrack(song) {
  if (!song || typeof song !== 'object') return song
  const rawUrl = String(song.url || '').trim()
  let spotify_url = rawUrl.includes('open.spotify.com') ? rawUrl : ''
  const sid = String(song.song_id || '').trim()
  if (!spotify_url && sid && !sid.startsWith('search-')) {
    spotify_url = `https://open.spotify.com/track/${sid}`
  }
  return {
    ...song,
    spotify_url,
    source: song.source || 'spotify',
  }
}

function useSearchManager() {
  function isValid(str) {
    return isValidSearch(str) || isValidURL(str) || isSpotifyPlaylistURL(str)
  }
  function isValidSearch(str) {
    const q = normalizeInput(str)
    if (!q || isAnySpotifyURL(q)) return false
    return true
  }
  function isValidURL(str) {
    return isSpotifyDirectDownloadURL(str)
  }

  function resetTextBrowse() {
    browseKind.value = 'text'
    playlistUrl.value = ''
    playlistTitle.value = ''
  }

  function loadSpotifyPlaylist(url) {
    const trimmed = normalizeInput(url)
    if (!trimmed || !isSpotifyPlaylistURL(trimmed)) return Promise.resolve()
    results.value = []
    isSearching.value = true
    error.value = false
    errorValue.value = ''
    browseKind.value = 'spotify_playlist'
    playlistUrl.value = trimmed
    searchTerm.value = trimmed
    try {
      sessionStorage.setItem(PLAYLIST_URL_KEY, trimmed)
    } catch {
      // ignore
    }
    return API.open(trimmed)
      .then((res) => {
        const data = res.data
        if (res.status !== 200) {
          error.value = true
          errorValue.value = `HTTP ${res.status}`
          results.value = []
          return
        }
        if (!Array.isArray(data)) {
          error.value = true
          errorValue.value = 'Playlist response was not a track list'
          results.value = []
          return
        }
        if (!data.length) {
          error.value = true
          errorValue.value = 'Playlist has no tracks'
          results.value = []
          return
        }
        const rows = data.map(enrichSpotifyTrack)
        results.value = rows
        const match = trimmed.match(/playlist\/([a-zA-Z0-9]+)/i)
        playlistTitle.value = match
          ? `Spotify playlist (${rows.length} tracks)`
          : 'Spotify playlist'
      })
      .catch((err) => {
        error.value = true
        errorValue.value =
          err?.response?.data?.detail || err?.message || String(err)
        results.value = []
      })
      .finally(() => {
        isSearching.value = false
      })
  }

  function searchFor(query) {
    const q = normalizeInput(query)
    if (!q || q === PLAYLIST_ROUTE_QUERY) {
      const stored = sessionStorage.getItem(PLAYLIST_URL_KEY)
      if (stored) return loadSpotifyPlaylist(stored)
      return Promise.resolve()
    }
    if (isSpotifyPlaylistURL(q)) {
      return loadSpotifyPlaylist(q)
    }
    if (isAnySpotifyURL(q)) {
      error.value = true
      errorValue.value =
        'Use the download button for track or album links; playlist links open as a track list.'
      results.value = []
      isSearching.value = false
      return Promise.resolve()
    }
    resetTextBrowse()
    results.value = []
    isSearching.value = true
    searchTerm.value = q
    error.value = false
    errorValue.value = ''
    return API.search(q)
      .then((res) => {
        if (res.status === 200) {
          results.value = (res.data || []).map((row) =>
            row?.source === 'spotify' ? enrichSpotifyTrack(row) : row
          )
          isSearching.value = false
        } else {
          isSearching.value = false
          error.value = true
          errorValue.value = res.toString()
        }
      })
      .catch((err) => {
        isSearching.value = false
        error.value = true
        errorValue.value = err.message
      })
  }

  return {
    searchTerm,
    isSearching,
    results,
    error,
    errorValue,
    browseKind,
    playlistUrl,
    playlistTitle,
    searchFor,
    loadSpotifyPlaylist,
    isValid,
    isValidSearch,
    isValidURL,
    isSpotifyPlaylistURL,
    isSpotifyDirectDownloadURL,
    PLAYLIST_ROUTE_QUERY,
  }
}

export { useSearchManager }
