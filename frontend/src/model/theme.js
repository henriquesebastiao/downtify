import { ref, computed } from 'vue'

const currentTheme = ref('')

const lightAlias = ref('light')
const darkAlias = ref('dark')

export function useBinaryThemeManager({
  useSystem = true,
  initialTheme = '',
  newLightAlias = '',
  newDarkAlias = '',
} = {}) {
  function setLightAlias(alias) {
    lightAlias.value = alias
    _updateDocument()
  }
  function setDarkAlias(alias) {
    darkAlias.value = alias
    _updateDocument()
  }

  function getSystemTheme() {
    const darkThemeMq = window.matchMedia('(prefers-color-scheme: dark)')
    if (darkThemeMq.matches) {
      return 'dark'
    } else {
      return 'light'
    }
  }

  function setTheme(newTheme) {
    currentTheme.value = newTheme
    _updateDocument()
  }

  function switchTheme() {
    if (currentTheme === 'dark') currentTheme.value = 'light'
    else if (currentTheme === 'light') currentTheme.value = 'dark'
    _updateDocument()
  }

  function _updateDocument() {
    document.documentElement.setAttribute(
      'data-theme',
      currentTheme.value === 'dark' ? darkAlias.value : lightAlias.value
    )
  }

  if (currentTheme.value !== 'light' && currentTheme.value !== 'dark') {
    if (useSystem) setTheme(getSystemTheme())
    if (initialTheme === 'light' || initialTheme === 'dark') {
      currentTheme.value = initialTheme
    }
  }
  if (newLightAlias) setLightAlias(newLightAlias)
  if (newDarkAlias) setDarkAlias(newDarkAlias)

  _updateDocument()

  return {
    currentTheme,
    setLightAlias,
    setDarkAlias,
    getSystemTheme,
    setTheme,
    switchTheme,
  }
}
