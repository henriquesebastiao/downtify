import { afterEach, describe, expect, it } from 'vitest'
import { AVAILABLE_LOCALES, setLocale, t } from '../i18n'
import en from '../i18n/locales/en.js'

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

function valueAt(obj, key) {
  return key.split('.').reduce((cur, k) => cur?.[k], obj)
}

const enKeys = allKeys(en).sort()
const placeholders = (text) =>
  [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

describe('i18n locale key consistency', () => {
  for (const { code, messages } of AVAILABLE_LOCALES) {
    describe(code, () => {
      it('has exactly the same keys as en', () => {
        expect(allKeys(messages).sort()).toEqual(enKeys)
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

  it('uses the locale plural rules', () => {
    setLocale('pt-BR')
    expect(t('common.tracks', { count: 2 })).toBe('2 faixas')
    expect(t('common.tracks', { count: 1 })).toBe('1 faixa')
  })

  it('returns the key when a message is missing', () => {
    expect(t('nope.missing')).toBe('nope.missing')
  })
})
