import { ref } from 'vue'
import monitorAPI from './monitor'
import { classifyInput } from '../lib/input'

// Watching an artist from their Library page. An artist watch follows a
// YouTube Music artist, so the name is looked up there, as the Monitor's
// artist suggestions do (GET /api/monitor/artist-suggestions/resolve):
// exactly one artist with that name is followed at once. Namesakes, none
// or a failed lookup open the dialog instead, to pick one by photo or
// paste the artist's link - never a guess from the name alone.
//
// These watches check daily and download new releases only: the library
// already has the artist, and a whole discography is the dialog's choice.
export const ARTIST_WATCH_INTERVAL = 1440
const ALL_RELEASE_TYPES = ['album', 'single', 'ep']

/** Whether `raw` is a link an artist watch accepts. */
export function isArtistLink(raw) {
  const input = classifyInput(raw)
  return (
    input.type === 'link' &&
    input.kind === 'artist' &&
    (input.source === 'spotify' || input.source === 'youtube')
  )
}

export function useArtistWatch() {
  const open = ref(false)
  // Looking the name up, or adding the watch.
  const busy = ref(false)
  const followed = ref(false)
  const candidates = ref([])
  const lookupFailed = ref(false)
  const url = ref('')
  // The link being added, while it is.
  const chosen = ref('')
  const error = ref('')
  const newOnly = ref(true)
  const releaseTypes = ref([...ALL_RELEASE_TYPES])
  // Bumped by reset: an answer for another artist is dropped.
  let generation = 0

  function reset() {
    generation++
    open.value = false
    busy.value = false
    followed.value = false
    candidates.value = []
    lookupFailed.value = false
    url.value = ''
    chosen.value = ''
    error.value = ''
    newOnly.value = true
    releaseTypes.value = [...ALL_RELEASE_TYPES]
  }

  // True once the server has accepted the watch. A refusal (already
  // watched, no artist with that exact name...) is shown in the dialog.
  async function add(link) {
    const current = generation
    busy.value = true
    chosen.value = link
    error.value = ''
    try {
      await monitorAPI.addMonitoredPlaylist(link, ARTIST_WATCH_INTERVAL, {
        new_only: newOnly.value,
        release_types: [...releaseTypes.value],
      })
      if (current !== generation) return false
      followed.value = true
      open.value = false
      return true
    } catch (err) {
      if (current !== generation) return false
      error.value = err?.response?.data?.detail || err?.message || ''
      open.value = true
      return false
    } finally {
      if (current === generation) {
        busy.value = false
        chosen.value = ''
      }
    }
  }

  async function follow(name) {
    if (busy.value || followed.value) return false
    const current = generation
    busy.value = true
    lookupFailed.value = false
    candidates.value = []
    error.value = ''
    let link = ''
    try {
      const { data } = await monitorAPI.resolveArtistSuggestion(name)
      if (current !== generation) return false
      link = data?.url || ''
      candidates.value = data?.candidates || []
    } catch {
      if (current !== generation) return false
      lookupFailed.value = true
    } finally {
      if (current === generation) busy.value = false
    }
    if (link) return add(link)
    open.value = true
    return false
  }

  function choose(candidate) {
    if (busy.value || !candidate?.url) return Promise.resolve(false)
    return add(candidate.url)
  }

  function submit() {
    if (busy.value || !isArtistLink(url.value)) return Promise.resolve(false)
    return add(classifyInput(url.value).url)
  }

  return {
    open,
    busy,
    followed,
    candidates,
    lookupFailed,
    url,
    chosen,
    error,
    newOnly,
    releaseTypes,
    reset,
    follow,
    choose,
    submit,
  }
}
