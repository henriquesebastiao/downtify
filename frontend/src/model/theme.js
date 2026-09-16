// Light / dark / follow-the-system theme, applied as
// <html data-theme="dark|light"> (see the tokens in index.css).
import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'downtify-theme'
const MODES = ['dark', 'light', 'system']

function readMode() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return MODES.includes(stored) ? stored : 'dark'
  } catch {
    return 'dark'
  }
}

const mode = ref(readMode())
const systemDark = ref(true)

if (typeof window !== 'undefined' && window.matchMedia) {
  const query = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = query.matches
  query.addEventListener?.('change', (event) => {
    systemDark.value = event.matches
  })
}

const resolved = computed(() => {
  if (mode.value === 'system') return systemDark.value ? 'dark' : 'light'
  return mode.value
})

function apply(theme) {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta)
    meta.setAttribute('content', theme === 'dark' ? '#0b0c0e' : '#f6f7f8')
}

watch(resolved, apply, { immediate: true })

function setMode(next) {
  if (!MODES.includes(next)) return
  mode.value = next
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // ignore
  }
}

function toggle() {
  setMode(resolved.value === 'dark' ? 'light' : 'dark')
}

export function useTheme() {
  return { mode, resolved, setMode, toggle, modes: MODES }
}
