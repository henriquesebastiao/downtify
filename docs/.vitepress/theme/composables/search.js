// Open state for the search dialog, shared by the top bar, the keyboard
// shortcut and the 404 page.
import { ref } from 'vue'

const open = ref(false)

export function useSearch() {
  return {
    open,
    show: () => (open.value = true),
    hide: () => (open.value = false),
  }
}
