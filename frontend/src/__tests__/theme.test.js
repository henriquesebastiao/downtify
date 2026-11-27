import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// No DOM here: just what the theme module touches.
const store = {}
globalThis.localStorage = {
  getItem: (key) => (key in store ? store[key] : null),
  setItem: (key, value) => {
    store[key] = String(value)
  },
  clear: () => {
    for (const key of Object.keys(store)) delete store[key]
  },
}
const attributes = {}
const barColor = { content: '' }
globalThis.document = {
  documentElement: {
    setAttribute: (name, value) => {
      attributes[name] = value
    },
    getAttribute: (name) => attributes[name] ?? null,
    removeAttribute: (name) => {
      delete attributes[name]
    },
  },
  querySelector: () => ({
    setAttribute: (_name, value) => {
      barColor.content = value
    },
  }),
}

// The theme module keeps its state at module level: each test loads a
// fresh copy over the saved choice it sets up.
async function loadTheme(saved = {}) {
  localStorage.clear()
  for (const [key, value] of Object.entries(saved)) {
    localStorage.setItem(key, value)
  }
  vi.resetModules()
  const { useTheme } = await import('/src/model/theme')
  return useTheme()
}

describe('theme', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('data-theme')
  })

  it('offers grey beside dark, light and system', async () => {
    const theme = await loadTheme()
    expect(theme.modes).toEqual(['dark', 'grey', 'light', 'system'])
  })

  it('applies a saved grey theme', async () => {
    const theme = await loadTheme({ 'downtify-theme': 'grey' })
    expect(theme.resolved.value).toBe('grey')
    expect(theme.isLight.value).toBe(false)
    expect(document.documentElement.getAttribute('data-theme')).toBe('grey')
    expect(barColor.content).toBe('#2b2d31')
  })

  it('remembers grey as the dark theme to toggle back to', async () => {
    const theme = await loadTheme()
    theme.setMode('grey')
    theme.toggle()
    await nextTick()
    expect(theme.resolved.value).toBe('light')
    expect(theme.toggleIcon.value).toBe('contrast')
    expect(theme.toggleLabel.value).toBe('settings.themeGrey')

    theme.toggle()
    await nextTick()
    expect(theme.resolved.value).toBe('grey')
    expect(localStorage.getItem('downtify-theme')).toBe('grey')
  })

  it('keeps the dark theme to go back to over a reload', async () => {
    const theme = await loadTheme({
      'downtify-theme': 'light',
      'downtify-theme-dark': 'grey',
    })
    theme.toggle()
    expect(theme.resolved.value).toBe('grey')
  })

  it('toggles back to dark when grey was never picked', async () => {
    const theme = await loadTheme({ 'downtify-theme': 'light' })
    expect(theme.toggleIcon.value).toBe('moon')
    theme.toggle()
    expect(theme.resolved.value).toBe('dark')
  })

  it('ignores an unknown saved theme', async () => {
    const theme = await loadTheme({ 'downtify-theme': 'purple' })
    expect(theme.resolved.value).toBe('dark')
    theme.setMode('purple')
    expect(theme.mode.value).toBe('dark')
  })
})
