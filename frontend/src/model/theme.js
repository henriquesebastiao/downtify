// Dark / grey / light / follow-the-system theme, applied as
// <html data-theme="dark|grey|light"> (see the tokens in tokens.css).
import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'downtify-theme'
// The dark theme the quick toggle (top bar, phone menu) goes back to
// from light: dark or grey, whichever was picked last.
const DARK_KEY = 'downtify-theme-dark'
const MODES = ['dark', 'grey', 'light', 'system']
const DARK_THEMES = ['dark', 'grey']
// The browser bar's colour on phones: each theme's background.
const BAR_COLORS = { dark: '#0b0c0e', grey: '#2b2d31', light: '#f6f7f8' }

function readStored(key, allowed, fallback) {
  try {
    const stored = localStorage.getItem(key)
    return allowed.includes(stored) ? stored : fallback
  } catch {
    return fallback
  }
}

function store(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // ignore
  }
}

const mode = ref(readStored(STORAGE_KEY, MODES, 'dark'))
const darkTheme = ref(
  DARK_THEMES.includes(mode.value)
    ? mode.value
    : readStored(DARK_KEY, DARK_THEMES, 'dark')
)
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
// Grey counts as dark for the toggle and its icon.
const isLight = computed(() => resolved.value === 'light')

function apply(theme) {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', BAR_COLORS[theme] || BAR_COLORS.dark)
}

watch(resolved, apply, { immediate: true })

function setMode(next) {
  if (!MODES.includes(next)) return
  mode.value = next
  store(STORAGE_KEY, next)
  if (DARK_THEMES.includes(next)) {
    darkTheme.value = next
    store(DARK_KEY, next)
  }
}

// What the toggle shows while the light theme is on: the theme it goes
// back to (an icon and an i18n key).
const toggleIcon = computed(() =>
  darkTheme.value === 'grey' ? 'contrast' : 'moon'
)
const toggleLabel = computed(() =>
  darkTheme.value === 'grey' ? 'settings.themeGrey' : 'settings.themeDark'
)

// Light, or back to the dark theme last picked (dark or grey).
function toggle() {
  setMode(isLight.value ? darkTheme.value : 'light')
}

export function useTheme() {
  return {
    mode,
    resolved,
    isLight,
    darkTheme,
    toggleIcon,
    toggleLabel,
    setMode,
    toggle,
    modes: MODES,
  }
}
