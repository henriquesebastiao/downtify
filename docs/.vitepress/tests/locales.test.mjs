import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { redirectToLocale } from '../lib/locale-redirect.mjs'
import { structureOf } from '../lib/page-structure.mjs'
import { LOCALES, SOURCE_LOCALE, TRANSLATED } from '../locales/index.mjs'
import { NAV } from '../nav.mjs'
import { isStub } from '../scripts/i18n.mjs'

const docs = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const pages = NAV.flatMap((entry) =>
  entry.items ? entry.items.map((item) => item.page) : [entry.page]
)
const read = (...parts) => fs.readFileSync(path.join(docs, ...parts), 'utf8')

/** Every text of an object as `[path, text]`, nested ones as `a/b/c`. */
function leaves(value, prefix = '') {
  return Object.entries(value).flatMap(([key, item]) =>
    item && typeof item === 'object'
      ? leaves(item, `${prefix}${key}/`)
      : [[`${prefix}${key}`, item]]
  )
}
const keysOf = (value) => leaves(value).map(([key]) => key)

describe('locale files', () => {
  const source = LOCALES[SOURCE_LOCALE]

  it.each(TRANSLATED)('%s has every key English has, and no others', (code) => {
    expect(keysOf(LOCALES[code]).sort()).toEqual(keysOf(source).sort())
  })

  it.each(Object.keys(LOCALES))('%s has no empty text', (code) => {
    const empty = leaves(LOCALES[code])
      .filter(([, value]) => typeof value === 'string' && !value.trim())
      .map(([key]) => key)
    expect(empty).toEqual([])
  })

  it.each(TRANSLATED)(
    '%s keeps the {placeholders} of the English text',
    (code) => {
      const bad = []
      for (const key of Object.keys(source.ui)) {
        const want = (source.ui[key].match(/\{\w+\}/g) || []).sort()
        const got = (LOCALES[code].ui[key].match(/\{\w+\}/g) || []).sort()
        if (want.join() !== got.join()) bad.push(key)
      }
      expect(bad).toEqual([])
    }
  )

  it('names every sidebar page and group', () => {
    for (const entry of NAV) {
      if (entry.items) {
        expect(source.nav.groups[entry.title]).toBeTruthy()
        for (const item of entry.items)
          expect(source.nav.pages[item.page]).toBeTruthy()
      } else {
        expect(source.nav.pages[entry.page]).toBeTruthy()
      }
    }
  })
})

describe('translated pages', () => {
  for (const code of TRANSLATED) {
    describe(code, () => {
      it('has every page, translated or as an English-only stub', () => {
        const missing = pages.filter(
          (page) => !fs.existsSync(path.join(docs, code, page))
        )
        expect(missing).toEqual([])
      })

      it('has stubs that include the English page', () => {
        for (const page of pages) {
          const file = path.join(docs, code, page)
          if (!isStub(file)) continue
          const include = /<!--@include: ([^>]+?)-->/.exec(read(code, page))
          const target = path.resolve(path.dirname(file), include[1].trim())
          expect(target, `${code}/${page}`).toBe(path.join(docs, page))
        }
      })

      for (const page of pages) {
        const file = path.join(docs, code, page)
        if (!fs.existsSync(file) || isStub(file)) continue
        it(`${page} has the structure of the English page`, () => {
          const english = structureOf(read(page))
          const translated = structureOf(read(code, page), TRANSLATED)
          expect(translated).toEqual(english)
        })
      }
    })
  }
})

describe('redirectToLocale', () => {
  const codes = TRANSLATED

  function visit(
    path,
    { languages = [], saved = null, search = '', hash = '' } = {}
  ) {
    const go = []
    const w = {
      location: {
        pathname: path,
        search,
        hash,
        replace: (url) => go.push(url),
      },
      navigator: { languages, language: languages[0] },
      localStorage: { getItem: () => saved },
    }
    redirectToLocale(codes, '/', w)
    return go[0] || null
  }

  it('opens a translated page in the browser’s language', () => {
    expect(visit('/features/users/', { languages: ['pt-BR', 'en'] })).toBe(
      '/pt-BR/features/users/'
    )
    expect(visit('/', { languages: ['de'] })).toBe('/de/')
  })

  it('matches by language when the region is not translated', () => {
    expect(visit('/', { languages: ['es-MX'] })).toBe('/es/')
    expect(visit('/', { languages: ['pt'] })).toBe('/pt-BR/')
    expect(visit('/', { languages: ['fr-CA'] })).toBe('/fr/')
    expect(visit('/', { languages: ['pt-br'] })).toBe('/pt-BR/')
  })

  it('stays in English without a translation', () => {
    expect(visit('/', { languages: ['ja', 'zh-CN'] })).toBeNull()
    expect(visit('/', { languages: ['en-US'] })).toBeNull()
    expect(visit('/', { languages: [] })).toBeNull()
  })

  it('uses the first language that matches anything', () => {
    expect(visit('/', { languages: ['ja', 'ko', 'de'] })).toBe('/ko/')
    expect(visit('/', { languages: ['en-GB', 'de'] })).toBeNull()
  })

  it('lets a saved pick win over the browser', () => {
    expect(visit('/', { languages: ['de'], saved: 'en' })).toBeNull()
    expect(visit('/', { languages: ['en'], saved: 'tr' })).toBe('/tr/')
    expect(visit('/', { languages: ['de'], saved: 'xx' })).toBe('/de/')
  })

  it('keeps the query and the section being read', () => {
    expect(
      visit('/features/users/', {
        languages: ['de'],
        search: '?q=1',
        hash: '#sharing-playlists',
      })
    ).toBe('/de/features/users/?q=1#sharing-playlists')
  })

  it('leaves pages that are already translated alone', () => {
    expect(visit('/pt-BR/features/users/', { languages: ['de'] })).toBeNull()
    expect(visit('/de', { languages: ['ko'] })).toBeNull()
  })
})
