import { ref } from 'vue'

const libraryFilterQuery = ref('')

function useLibraryFilter() {
  function setLibraryFilter(query) {
    libraryFilterQuery.value = String(query || '').trim()
  }

  function clearLibraryFilter() {
    libraryFilterQuery.value = ''
  }

  return {
    libraryFilterQuery,
    setLibraryFilter,
    clearLibraryFilter,
  }
}

function libraryEntryMatchesQuery(entry, query) {
  const q = String(query || '')
    .trim()
    .toLowerCase()
  if (!q) return true
  const terms = q.split(/\s+/).filter(Boolean)
  const haystack = [
    entry?.title,
    entry?.artist,
    entry?.album,
    entry?.file,
    ...(Array.isArray(entry?.playlists) ? entry.playlists : []),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return terms.every((term) => haystack.includes(term))
}

export { useLibraryFilter, libraryEntryMatchesQuery }
