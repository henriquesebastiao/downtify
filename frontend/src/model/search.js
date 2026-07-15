import { ref } from 'vue'

import API from '/src/model/api'
import { useSettingsManager } from '/src/model/settings'

const searchTerm = ref('')
const results = ref()
const albumResults = ref([])
const isSearching = ref(false)
const error = ref(false)
const errorValue = ref('')

function isYouTubeURL(str) {
  if (!/youtube\.com\/|youtu\.be\//.test(str)) return false
  return (
    /[?&]v=/.test(str) ||
    str.includes('youtu.be/') ||
    /\/browse\/MPREb_/.test(str) ||
    (str.includes('/playlist?') && /list=OLAK5uy_/.test(str))
  )
}

function useSearchManager() {
  const settingsManager = useSettingsManager()

  function isValid(str) {
    return isValidSearch(str) || isValidURL(str)
  }
  function isValidSearch(str) {
    if (
      str === '' ||
      str.includes('://open.spotify.com/track/') ||
      str.includes('://open.spotify.com/album/') ||
      str.includes('://open.spotify.com/playlist/') ||
      str.includes('://open.spotify.com/show/') ||
      str.includes('://open.spotify.com/artist/') ||
      isYouTubeURL(str)
    ) {
      return false
    }
    return true
  }
  function isValidURL(str) {
    return (
      str.includes('://open.spotify.com/track/') ||
      str.includes('://open.spotify.com/album/') ||
      str.includes('://open.spotify.com/playlist/') ||
      isYouTubeURL(str)
    )
  }

  function searchFor(query) {
    console.log('Searching for:', query)
    results.value = []
    albumResults.value = []
    isSearching.value = true
    searchTerm.value = query
    error.value = false
    errorValue.value = ''
    API.search(query)
      .then((res) => {
        console.log('Received Search Data:', res.data)
        if (res.status === 200) {
          results.value = res.data
          isSearching.value = false
        } else {
          console.error('Error Searching:', res)
          isSearching.value = false
          error.value = true
          errorValue.value = res.toString()
        }
      })
      .catch((err) => {
        console.error('Other Error Searching:', err.message)
        isSearching.value = false
        error.value = true
        errorValue.value = err.message
      })
    if (settingsManager.settings.value.search_albums !== false) {
      API.searchAlbums(query)
        .then((res) => {
          console.log('Received Album Search Data:', res.data)
          if (res.status === 200) {
            albumResults.value = res.data
          }
        })
        .catch((err) => {
          // Album search is a secondary, best-effort addition to the main
          // song list — a failure here should not surface as a page error.
          console.error('Album search error:', err.message)
        })
    }
  }

  return {
    searchTerm,
    isSearching,
    results,
    albumResults,
    error,
    errorValue,
    searchFor,
    isValid,
    isValidSearch,
    isValidURL,
  }
}

export { useSearchManager }
