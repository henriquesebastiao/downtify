// Existing Similar page: local sound analysis and explicitly enabled external radio.
import { computed, ref, watch } from 'vue'
import { libraryOnly } from '/src/model/musicPolicy'

import { musicAI } from '/src/model/musicAI'
import { useLibrary } from '/src/model/library'

const artist = ref('')
const track = ref('')
const tracks = ref([])
const loading = ref(false)
const error = ref('')
const searched = ref(false)
const source = ref('local')
const selection = ref({})
const localEnabled = computed(
  () => musicAI.capabilities.value?.features?.similarity === true
)
const externalEnabled = computed(
  () => musicAI.capabilities.value?.features?.external_beta === true
)
const canSearch = computed(() => localEnabled.value || externalEnabled.value)
// The endless list: the radio mix is finite per request, so pages are
// chained by seeding each request from the last row.
const hasMore = ref(true)
const loadingMore = ref(false)
let serial = 0
watch(libraryOnly, clear)
watch(() => musicAI.account?.value, clear)
watch(
  () => musicAI.capabilities.value?.features,
  (flags) => {
    if (
      source.value === 'external' &&
      !flags?.external_beta &&
      flags?.similarity
    )
      setSource('local')
    if (source.value === 'local' && !flags?.similarity && flags?.external_beta)
      setSource('external')
    if (!flags?.[source.value === 'local' ? 'similarity' : 'external_beta'])
      clear()
  },
  { immediate: true }
)

async function fetchTracks(
  artist,
  track,
  mine = serial,
  choice = source.value,
  selected = selection.value,
  owner = musicAI.account?.value
) {
  await musicAI.refresh()
  if (mine !== serial || owner !== musicAI.account?.value)
    throw new Error('Recherche remplacée.')
  if (choice === 'local') {
    if (!localEnabled.value)
      throw new Error('La similarité locale est désactivée.')
    return Object.keys(selected).length
      ? musicAI.similar(artist, track, selected)
      : musicAI.similar(artist, track)
  }
  if (!externalEnabled.value) {
    throw new Error('La découverte externe bêta est désactivée.')
  }
  return musicAI.externalSimilar(artist, track)
}

function setSource(value) {
  if (!['local', 'external'].includes(value)) throw new Error('Unknown source')
  if (source.value !== value) clear()
  source.value = value
}

function songKey(item) {
  const id = String(item?.song_id || '')
    .trim()
    .toLowerCase()
  if (id) return `id:${id}`
  const a = String(
    (Array.isArray(item?.artists) ? item.artists[0] : item?.artist) || ''
  )
    .trim()
    .toLowerCase()
  const n = String(item?.name || '')
    .trim()
    .toLowerCase()
  return `${a}|${n}`
}

async function searchFor(seedArtist, seedTrack, exact = {}) {
  selection.value = exact
  const a = String(seedArtist || '').trim()
  const t = String(seedTrack || '').trim()
  artist.value = a
  track.value = t
  if (!a && !t) {
    tracks.value = []
    searched.value = false
    hasMore.value = true
    return
  }
  const mine = ++serial
  loading.value = true
  loadingMore.value = false
  hasMore.value = source.value === 'external'
  error.value = ''
  searched.value = true
  try {
    const res = await fetchTracks(a, t)
    if (mine !== serial) return
    tracks.value = res.data?.tracks || []
  } catch (err) {
    if (mine !== serial) return
    tracks.value = []
    error.value = err?.response?.data?.detail || err?.message || 'Search failed'
  } finally {
    if (mine === serial) loading.value = false
  }
}

/**
 * Append the next page, seeded from the last row. Returns what was added.
 * A page that adds nothing new (or fails) ends the list.
 */
async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return []
  const list = tracks.value
  if (!list.length) return []
  const seed = list[list.length - 1]
  const seedArtist = String(
    (Array.isArray(seed.artists) ? seed.artists[0] : seed.artist) || ''
  ).trim()
  const seedTrack = String(seed.name || '').trim()
  if (!seedArtist || !seedTrack) {
    hasMore.value = false
    return []
  }
  const mine = serial
  loadingMore.value = true
  try {
    const res = await fetchTracks(seedArtist, seedTrack)
    if (mine !== serial) return []
    const fresh = (res.data?.tracks || []).filter(
      (item) => !list.some((known) => songKey(known) === songKey(item))
    )
    if (fresh.length) {
      tracks.value = [...list, ...fresh]
      return fresh
    }
    hasMore.value = false
    return []
  } catch {
    // A failed page just ends the endless list; what loaded stays playable.
    if (mine === serial) hasMore.value = false
    return []
  } finally {
    loadingMore.value = false
  }
}

function clear() {
  serial += 1
  artist.value = ''
  track.value = ''
  tracks.value = []
  loading.value = false
  loadingMore.value = false
  hasMore.value = true
  error.value = ''
  searched.value = false
}

export function useSimilar() {
  const library = useLibrary()
  // The library refreshes itself after downloads; rows follow it so a
  // downloaded similar track shows as in-library without re-searching.
  // Rows already carry their video id and link, so they download and
  // stream directly.
  const songs = computed(() =>
    tracks.value.map((item) => ({
      song_id: item.song_id || '',
      ...(item.file ? { file: item.file, source: 'library' } : {}),
      name: item.name || '',
      artists: Array.isArray(item.artists)
        ? item.artists
        : [item.artist].filter(Boolean),
      artist: item.artist || '',
      album_name: item.album_name || '',
      cover_url: item.cover_url || '',
      duration: item.duration || 0,
      url: item.url || '',
      match: item.match || 0,
    }))
  )
  return {
    source,
    localEnabled,
    externalEnabled,
    canSearch,
    setSource,
    capabilities: musicAI.capabilities,
    artist,
    track,
    tracks,
    songs,
    loading,
    loadingMore,
    hasMore,
    error,
    searched,
    searchFor,
    loadMore,
    clear,
    lookupSongs: library.lookupSongs,
  }
}
