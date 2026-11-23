import { ref, shallowReactive } from 'vue'
import en from './locales/en.js'

// Registry of available locales. To add a new language:
//   1. Create ./locales/<code>.js exporting the same key shape as en.js
//   2. Add an entry below — `code` is the value stored in localStorage
//      and the file's name, `name` is the label shown in the language
//      picker.
// Only English (the fallback) ships with the app: every other language is
// its own file, fetched the first time it is shown (`loadLocale`).
export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Español' },
  { code: 'pt-BR', name: 'Português (BR)' },
  { code: 'el', name: 'Ελληνικά' },
  { code: 'fr', name: 'Français' },
  { code: 'tr', name: 'Türkçe' },
  { code: 'hu', name: 'Magyar' },
  { code: 'bg', name: 'Български' },
  { code: 'de', name: 'Deutsch' },
  { code: 'ko', name: '한국어' },
  { code: 'ru', name: 'Русский' },
  { code: 'zh-CN', name: '简体中文' },
  { code: 'zh-TW', name: '繁體中文' },
]

const DEFAULT_LOCALE = 'en'
const STORAGE_KEY = 'downtify-locale'

const loaders = import.meta.glob(['./locales/*.js', '!./locales/en.js'])
// The messages of every language loaded so far, by code.
const catalogs = shallowReactive({ [DEFAULT_LOCALE]: en })

const known = (code) => AVAILABLE_LOCALES.some((l) => l.code === code)

/** Fetch a language's messages (once); resolves to them, or null. */
export async function loadLocale(code) {
  if (catalogs[code]) return catalogs[code]
  const load = loaders[`./locales/${code}.js`]
  if (!load) return null
  const messages = (await load()).default
  catalogs[code] = messages
  return messages
}

const stored = (() => {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
})()

const initial = known(stored) ? stored : DEFAULT_LOCALE

// The language picked, and the one on screen: they differ only while a
// newly picked language is still being fetched, so the page keeps the
// previous one meanwhile instead of flashing English.
export const currentLocale = ref(initial)
const shownLocale = ref(DEFAULT_LOCALE)

function show(code) {
  return loadLocale(code)
    .then(() => {
      if (currentLocale.value === code && catalogs[code]) {
        shownLocale.value = code
      }
    })
    .catch(() => {
      // Offline or gone: English stays on screen, the next pick retries.
    })
}

/** Resolves once the starting language is on screen (main.js waits). */
export const localeReady = show(initial)

const PLURAL_FORMS = ['zero', 'one', 'two', 'few', 'many', 'other']

/** `{ one: '…', other: '…' }` — a message with plural forms. */
function isPlural(value) {
  return (
    value !== null &&
    typeof value === 'object' &&
    typeof value.other === 'string' &&
    Object.keys(value).every((form) => PLURAL_FORMS.includes(form))
  )
}

function lookup(messages, key) {
  if (!messages) return undefined
  const parts = key.split('.')
  let cur = messages
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = cur[p]
  }
  return typeof cur === 'string' || isPlural(cur) ? cur : undefined
}

const numberFormats = new Map()
const pluralRules = new Map()

function cached(map, code, make) {
  if (!map.has(code)) map.set(code, make(code))
  return map.get(code)
}

function format(template, params, code) {
  if (!params) return template
  const numbers = cached(numberFormats, code, (c) => new Intl.NumberFormat(c))
  return template.replace(/\{(\w+)\}/g, (_, name) => {
    const value = params[name]
    if (value === undefined || value === null) return `{${name}}`
    return typeof value === 'number' ? numbers.format(value) : String(value)
  })
}

export function t(key, params) {
  const code = shownLocale.value
  let msg = lookup(catalogs[code], key)
  let msgCode = code
  if (msg === undefined && code !== DEFAULT_LOCALE) {
    msg = lookup(catalogs[DEFAULT_LOCALE], key)
    msgCode = DEFAULT_LOCALE
  }
  if (msg === undefined) return key
  if (isPlural(msg)) {
    const rules = cached(pluralRules, msgCode, (c) => new Intl.PluralRules(c))
    const count = Number(params?.count ?? 0)
    msg = msg[rules.select(count)] ?? msg.other
  }
  return format(msg, params, code)
}

/**
 * Pick a language. The choice is made (and saved) at once; the returned
 * promise resolves when its messages are on screen.
 */
export function setLocale(code) {
  if (!known(code)) return Promise.resolve()
  currentLocale.value = code
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // ignore storage errors (private mode, etc.)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', code)
  }
  if (catalogs[code]) {
    shownLocale.value = code
    return Promise.resolve()
  }
  return show(code)
}

export function useI18n() {
  return {
    t,
    locale: currentLocale,
    setLocale,
    locales: AVAILABLE_LOCALES,
  }
}

// Apply on initial load
if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', currentLocale.value)
}
