// Light / dark / follow-the-system, stored like the app does and applied
// as <html data-theme>. The inline script in config.mjs applies the saved
// choice before the first paint; this keeps it in sync afterwards.
import { computed, ref } from 'vue'

const STORAGE_KEY = 'downtify-theme'
export const MODES = ['light', 'dark', 'system']

const mode = ref('system')
const systemDark = ref(true)
let started = false

const resolved = computed(() =>
  mode.value === 'system' ? (systemDark.value ? 'dark' : 'light') : mode.value
)

function apply() {
  const theme = resolved.value
  document.documentElement.setAttribute('data-theme', theme)
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', theme === 'dark' ? '#0b0c0e' : '#f6f7f8')
}

/** Call once on the client (after mount). */
export function startThemeMode() {
  if (started) return
  started = true
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (MODES.includes(stored)) mode.value = stored
  } catch {
    // Storage blocked: follow the system.
  }
  const query = matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = query.matches
  query.addEventListener('change', (event) => {
    systemDark.value = event.matches
    apply()
  })
  apply()
}

function setMode(next) {
  if (!MODES.includes(next)) return
  mode.value = next
  try {
    if (next === 'system') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // Not persisted; still applied for this visit.
  }
  apply()
}

export function useThemeMode() {
  return { mode, resolved, setMode }
}
