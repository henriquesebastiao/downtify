import { afterEach, describe, expect, it } from 'vitest'
import { AVAILABLE_LOCALES, loadLocale, setLocale, t } from '../i18n'
import en from '../i18n/locales/en.js'

// Every language file, read up front: the app only fetches the one in use.
const files = import.meta.glob('../i18n/locales/*.js', {
  eager: true,
  import: 'default',
})
const catalogs = AVAILABLE_LOCALES.map(({ code }) => ({
  code,
  messages: files[`../i18n/locales/${code}.js`],
}))

/**
 * Recursively collect every dotted key path in an i18n object.
 * e.g. { settings: { title: '…' } }  →  ['settings.title']
 * Plural messages ({ one, other }) contribute one path per form.
 */
function allKeys(obj, prefix = '') {
  return Object.entries(obj).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof value === 'object' && value !== null
      ? allKeys(value, path)
      : [path]
  })
}

/** Dotted key paths, treating each plural message as a single leaf. */
function shapeKeys(obj, prefix = '') {
  return Object.entries(obj).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    if (typeof value !== 'object' || value === null) return [path]
    const forms = Object.keys(value)
    return forms.length && forms.every((f) => PLURAL_FORMS.includes(f))
      ? [path]
      : shapeKeys(value, path)
  })
}

function valueAt(obj, key) {
  return key.split('.').reduce((cur, k) => cur?.[k], obj)
}

const PLURAL_FORMS = ['zero', 'one', 'two', 'few', 'many', 'other']
const pluralNode = (value) =>
  typeof value === 'object' &&
  value !== null &&
  Object.keys(value).length > 0 &&
  Object.keys(value).every((form) => PLURAL_FORMS.includes(form))

const enKeys = allKeys(en).sort()
const placeholders = (text) =>
  [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('i18n locale key consistency', () => {
  it('has a file for every listed language, and lists every file', () => {
    expect(catalogs.every(({ messages }) => messages)).toBe(true)
    expect(Object.keys(files).length).toBe(AVAILABLE_LOCALES.length)
  })

  for (const { code, messages } of catalogs) {
    describe(code, () => {
      it('has exactly the same key shape as en', () => {
        // Every plural message maps to one path, so a language may add
        // the plural forms it needs (e.g. Russian's `few`/`many`)
        // without losing one-to-one key parity.
        expect(shapeKeys(messages).sort()).toEqual(shapeKeys(en).sort())
      })

      it('declares plural messages where en has them, with an `other` form', () => {
        for (const key of shapeKeys(en)) {
          const enValue = valueAt(en, key)
          if (!pluralNode(enValue)) continue
          const value = valueAt(messages, key)
          if (!pluralNode(value)) {
            throw new Error(
              `${code}: plural message at "${key}" must stay a message object`
            )
          }
          const forms = Object.keys(value)
          expect(
            forms.every((f) => PLURAL_FORMS.includes(f)),
            `${code}: unknown plural form at "${key}"`
          ).toBe(true)
          expect(value.other, `${code}: "${key}" needs "other"`).toBeTruthy()
          for (const form of forms) {
            // `one` may drop {count} ("Every hour") or keep it where the
            // language's `one` also covers 21, 31… (Russian).
            if (form === 'one') continue
            // Forms that en also has share its placeholders; forms that
            // only this language has share en's `other` placeholders.
            const expected = form in enValue ? enValue[form] : enValue.other
            expect(
              placeholders(value[form]).sort(),
              `${code}: "${key}.${form}"`
            ).toEqual(placeholders(expected).sort())
          }
        }
      })

      it('declares a language name', () => {
        expect(messages.language.name.length).toBeGreaterThan(0)
      })

      it('has no empty strings', () => {
        for (const key of allKeys(messages)) {
          expect(valueAt(messages, key), `${code}: "${key}" is empty`).not.toBe(
            ''
          )
        }
      })

      it('uses the same placeholders as en', () => {
        for (const key of enKeys) {
          // `one` forms may drop {count} ("Every hour").
          if (key.endsWith('.one')) continue
          const theirs = placeholders(valueAt(messages, key))
          const ours = placeholders(valueAt(en, key))
          expect(theirs, `${code}: "${key}"`).toEqual(ours)
        }
      })
    })
  }
})

describe('t()', () => {
  afterEach(() => setLocale('en'))

  it('interpolates params', () => {
    expect(t('search.resultsFor', { query: 'abc' })).toBe('Results for “abc”')
  })

  it('picks plural forms from count', () => {
    expect(t('common.tracks', { count: 1 })).toBe('1 track')
    expect(t('common.tracks', { count: 3 })).toBe('3 tracks')
    expect(t('monitor.everyHours', { count: 1 })).toBe('Every hour')
  })

  it('formats numbers for the locale', () => {
    expect(t('common.tracks', { count: 1200 })).toBe('1,200 tracks')
  })

  it('uses the locale plural rules', async () => {
    await setLocale('pt-BR')
    expect(t('common.tracks', { count: 2 })).toBe('2 faixas')
    expect(t('common.tracks', { count: 1 })).toBe('1 faixa')
  })

  it('returns the key when a message is missing', () => {
    expect(t('nope.missing')).toBe('nope.missing')
  })
})

describe('loading languages on demand', () => {
  afterEach(() => setLocale('en'))

  it('keeps the language on screen until the picked one is in', async () => {
    await setLocale('en')
    const picking = setLocale('de')
    // Picked at once, still English on screen until German arrives.
    expect(t('nav.library')).toBe('Library')
    await picking
    expect(t('nav.library')).toBe(files['../i18n/locales/de.js'].nav.library)
  })

  it('shows only the last pick when two overlap', async () => {
    const first = setLocale('fr')
    const second = setLocale('es')
    await Promise.all([first, second])
    expect(t('nav.library')).toBe(files['../i18n/locales/es.js'].nav.library)
  })

  it('loads a language once and knows no others', async () => {
    const messages = await loadLocale('ko')
    expect(await loadLocale('ko')).toBe(messages)
    expect(await loadLocale('xx')).toBeNull()
  })
})
