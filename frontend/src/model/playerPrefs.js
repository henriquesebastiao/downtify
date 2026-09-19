// Player display preferences. Kept per device, like the theme: what one
// screen wants to see says nothing about another's.
import { useLocalStorage } from '@vueuse/core'

// Only hides the lyrics; the files keep the ones Downtify embedded, and
// "Download lyrics" (a server setting) is untouched.
const showLyrics = useLocalStorage('downtify-show-lyrics', true)

export function usePlayerPrefs() {
  return { showLyrics }
}
