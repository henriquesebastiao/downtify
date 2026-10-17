import { ref } from 'vue'
import monitorAPI from './monitor'
import { classifyInput } from '../lib/input'

// A known Spotify identity can be followed directly. Otherwise the user
// supplies the identity: never guess a different artist from a name.
export function useArtistWatch() {
  const open = ref(false)
  const url = ref('')
  const busy = ref(false)
  const followed = ref(false)
  const error = ref('')
  const newOnly = ref(true)
  const releaseTypes = ref(['album', 'single', 'ep'])

  function reset() {
    open.value = false
    url.value = ''
    followed.value = false
    error.value = ''
    newOnly.value = true
    releaseTypes.value = ['album', 'single', 'ep']
  }

  async function submit() {
    if (busy.value) return false
    const input = classifyInput(url.value)
    if (input.kind !== 'artist' || input.source !== 'spotify') return false
    busy.value = true
    error.value = ''
    try {
      await monitorAPI.addMonitoredPlaylist(input.url, 1440, {
        new_only: newOnly.value,
        release_types: [...releaseTypes.value],
      })
      followed.value = true
      open.value = false
      return true
    } catch (err) {
      error.value = err?.response?.data?.detail || err?.message || ''
      open.value = true
      return false
    } finally {
      busy.value = false
    }
  }

  async function follow(spotifyId) {
    if (busy.value || followed.value) return false
    const id = String(spotifyId || '').trim()
    if (!/^[A-Za-z0-9]{22}$/.test(id)) {
      open.value = true
      return false
    }
    url.value = `https://open.spotify.com/artist/${id}`
    return submit()
  }

  return {
    open,
    url,
    busy,
    followed,
    error,
    newOnly,
    releaseTypes,
    reset,
    submit,
    follow,
  }
}
