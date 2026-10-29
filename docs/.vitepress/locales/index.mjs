// The documentation's languages. English is the source and lives at the
// site root; every other language has a folder named after its code
// (`docs/pt-BR/…` → `/pt-BR/…`) with the same pages as English, and a file
// here with the site's own text. They are independent of the app's
// languages (frontend/src/i18n/locales), though today they are the same.
import bg from './bg.mjs'
import de from './de.mjs'
import el from './el.mjs'
import en from './en.mjs'
import es from './es.mjs'
import fr from './fr.mjs'
import hu from './hu.mjs'
import ko from './ko.mjs'
import ptBR from './pt-BR.mjs'
import tr from './tr.mjs'

export const SOURCE_LOCALE = 'en'

/** Every locale, English first. */
export const LOCALES = {
  en,
  bg,
  de,
  el,
  es,
  fr,
  hu,
  ko,
  'pt-BR': ptBR,
  tr,
}

/** Codes of the translated locales (everything but English). */
export const TRANSLATED = Object.keys(LOCALES).filter(
  (code) => code !== SOURCE_LOCALE
)

/** Where a locale's pages live: `/` for English, `/pt-BR/` for others. */
export const localePrefix = (code) =>
  code === SOURCE_LOCALE ? '/' : `/${code}/`
