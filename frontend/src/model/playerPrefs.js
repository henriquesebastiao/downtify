// Player preferences remembered in this browser, like the theme.
// Lyrics and normalization enablement also follow the signed-in account
// (see model/account.js); the playback level stays local to this browser.
import { useLocalStorage } from '@vueuse/core'
import { computed } from 'vue'

// Only hides the lyrics; the files keep the ones Downtify embedded, and
// "Download lyrics" (a server setting) is untouched.
const showLyrics = useLocalStorage('downtify-show-lyrics', true)
const normalizeVolume = useLocalStorage('downtify-normalize-volume', false)
const storedNormalizationLevel = useLocalStorage(
  'downtify-normalization-level',
  'normal'
)
const levels = ['normal', 'louder', 'maximum']
const normalizationLevel = computed({
  get: () =>
    levels.includes(storedNormalizationLevel.value)
      ? storedNormalizationLevel.value
      : 'normal',
  set: (value) => {
    storedNormalizationLevel.value = levels.includes(value) ? value : 'normal'
  },
})

export function usePlayerPrefs() {
  return { showLyrics, normalizeVolume, normalizationLevel }
}
