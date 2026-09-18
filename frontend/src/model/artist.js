import { ref } from 'vue'

import API from '/src/model/api'

const artist = ref(null)
const loading = ref(false)
const error = ref(false)
const errorValue = ref('')

function useArtistManager() {
  function reset() {
    artist.value = null
    error.value = false
    errorValue.value = ''
  }

  function fetch(url, limit = 5) {
    loading.value = true
    error.value = false
    errorValue.value = ''
    return API.getArtistTopSongsFromUrl(url, limit)
      .then((res) => {
        artist.value = res.data
      })
      .catch((err) => {
        console.error('Error fetching artist top songs:', err.message)
        error.value = true
        errorValue.value = err.message
      })
      .finally(() => {
        loading.value = false
      })
  }

  return {
    artist,
    loading,
    error,
    errorValue,
    fetch,
    reset,
  }
}

export { useArtistManager }
