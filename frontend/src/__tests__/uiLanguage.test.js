import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { needsLanguageSync, splitUiLanguage } from '../lib/uiLanguage'

describe('needsLanguageSync', () => {
  it('is true when the server has no language, or another one', () => {
    expect(needsLanguageSync('', 'pt-BR')).toBe(true)
    expect(needsLanguageSync('en', 'pt-BR')).toBe(true)
    expect(needsLanguageSync(undefined, 'en')).toBe(true)
  })

  it('is false when the server is up to date', () => {
    expect(needsLanguageSync('pt-BR', 'pt-BR')).toBe(false)
  })

  it('is false when there is no language to send', () => {
    expect(needsLanguageSync('pt-BR', '')).toBe(false)
    expect(needsLanguageSync('', undefined)).toBe(false)
  })
})

describe('splitUiLanguage', () => {
  it('takes the language apart from the other settings', () => {
    expect(splitUiLanguage({ format: 'mp3', ui_language: 'fr' })).toEqual({
      uiLanguage: 'fr',
      rest: { format: 'mp3' },
    })
  })

  it('treats a missing or odd language as unknown', () => {
    expect(splitUiLanguage({ format: 'mp3' }).uiLanguage).toBe('')
    expect(splitUiLanguage({ ui_language: 42 }).uiLanguage).toBe('')
    expect(splitUiLanguage(null)).toEqual({ uiLanguage: '', rest: {} })
  })
})

// The settings module itself, with the API faked: it runs its sync on import,
// like it does when the app starts.
describe('the language sync in model/settings.js', () => {
  let api
  let i18n
  let store

  // Import the module the way a page load does: the server has `server` on
  // file, and the page is shown in `locale`.
  async function boot({ server, locale }) {
    vi.resetModules()
    store = {}
    globalThis.localStorage = {
      getItem: (key) => store[key] ?? null,
      setItem: (key, value) => {
        store[key] = value
      },
    }
    if (locale) store['downtify-locale'] = locale
    vi.doMock('/src/model/api', () => ({
      default: {
        getSettings: vi.fn(() => Promise.resolve({ data: { ...server } })),
        setSettings: vi.fn((payload) =>
          Promise.resolve({ data: { ...server, ...payload } })
        ),
      },
    }))
    api = (await import('/src/model/api')).default
    i18n = await import('../i18n/index.js')
    const settings = await import('../model/settings.js')
    await vi.waitFor(() =>
      expect(settings.useSettingsManager().loaded.value).toBe(true)
    )
    await nextTick()
    await Promise.resolve()
    return settings.useSettingsManager()
  }

  const sent = () => api.setSettings.mock.calls.map(([payload]) => payload)

  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.doUnmock('/src/model/api')
    delete globalThis.localStorage
  })

  it('tells the server the language when it has none (an upgrade)', async () => {
    await boot({ server: { format: 'mp3', ui_language: '' }, locale: 'pt-BR' })
    expect(sent()).toEqual([{ ui_language: 'pt-BR' }])
  })

  it('also tells it "en" to someone who never touched the picker', async () => {
    await boot({ server: { format: 'mp3' }, locale: null })
    expect(sent()).toEqual([{ ui_language: 'en' }])
  })

  it('says nothing when the server already has the language', async () => {
    await boot({ server: { ui_language: 'pt-BR' }, locale: 'pt-BR' })
    expect(api.setSettings).not.toHaveBeenCalled()
  })

  it('corrects the server when the page is shown in another language', async () => {
    await boot({ server: { ui_language: 'en' }, locale: 'es' })
    expect(sent()).toEqual([{ ui_language: 'es' }])
  })

  it('sends the new language when the picker changes it', async () => {
    await boot({ server: { ui_language: 'en' }, locale: 'en' })
    expect(api.setSettings).not.toHaveBeenCalled()
    i18n.setLocale('fr')
    await nextTick()
    await Promise.resolve()
    expect(sent()).toEqual([{ ui_language: 'fr' }])
    // Back to what the server now has: nothing more to say.
    i18n.setLocale('fr')
    await nextTick()
    expect(api.setSettings).toHaveBeenCalledTimes(1)
  })

  it('does not break the page when the server cannot be told', async () => {
    vi.resetModules()
    store = {}
    globalThis.localStorage = {
      getItem: (key) => store[key] ?? null,
      setItem: () => {},
    }
    store['downtify-locale'] = 'tr'
    vi.doMock('/src/model/api', () => ({
      default: {
        getSettings: vi.fn(() => Promise.resolve({ data: {} })),
        setSettings: vi.fn(() => Promise.reject(new Error('offline'))),
      },
    }))
    api = (await import('/src/model/api')).default
    const settings = await import('../model/settings.js')
    await vi.waitFor(() =>
      expect(settings.useSettingsManager().loaded.value).toBe(true)
    )
    await Promise.resolve()
    await Promise.resolve()
    expect(api.setSettings).toHaveBeenCalledTimes(1)
    expect(settings.useSettingsManager().loaded.value).toBe(true)
  })

  it('keeps the language out of what the settings page saves', async () => {
    const manager = await boot({
      server: { format: 'mp3', ui_language: 'pt-BR' },
      locale: 'pt-BR',
    })
    expect('ui_language' in manager.settings.value).toBe(false)
    expect(manager.dirty.value).toBe(false)

    await manager.saveSettings()
    const [payload] = api.setSettings.mock.calls.at(-1)
    // The whole form goes; the language is not part of it.
    expect(payload).not.toHaveProperty('ui_language')
    expect('ui_language' in manager.settings.value).toBe(false)
    expect(manager.dirty.value).toBe(false)
  })
})
