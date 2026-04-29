import { ref } from 'vue'
import en from './locales/en.js'
import es from './locales/es.js'
import ptBR from './locales/pt-BR.js'

// Registry of available locales. To add a new language:
//   1. Create ./locales/<code>.js exporting the same key shape as en.js
//   2. Import it above
//   3. Add an entry below — `code` is the value stored in localStorage,
//      `name` is the label shown in the language picker.
export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  { code: 'pt-BR', name: 'Português (BR)', messages: ptBR },
]

const DEFAULT_LOCALE = 'en'
const STORAGE_KEY = 'downtify-locale'

const stored = (() => {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
})()

const initial = AVAILABLE_LOCALES.find((l) => l.code === stored)
  ? stored
  : DEFAULT_LOCALE

export const currentLocale = ref(initial)

function localeData(code) {
  return (
    AVAILABLE_LOCALES.find((l) => l.code === code) ||
    AVAILABLE_LOCALES.find((l) => l.code === DEFAULT_LOCALE)
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
  return typeof cur === 'string' ? cur : undefined
}

function format(template, params) {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (_, name) =>
    params[name] !== undefined && params[name] !== null
      ? String(params[name])
      : `{${name}}`
  )
}

export function t(key, params) {
  const code = currentLocale.value
  let msg = lookup(localeData(code).messages, key)
  if (msg === undefined && code !== DEFAULT_LOCALE) {
    msg = lookup(localeData(DEFAULT_LOCALE).messages, key)
  }
  return format(msg !== undefined ? msg : key, params)
}

export function setLocale(code) {
  if (!AVAILABLE_LOCALES.find((l) => l.code === code)) return
  currentLocale.value = code
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // ignore storage errors (private mode, etc.)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', code)
  }
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
