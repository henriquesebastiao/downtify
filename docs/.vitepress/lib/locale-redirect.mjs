// Which language the docs open in. A reader who never picked one gets the
// language their browser prefers, when the docs are translated into it,
// and English otherwise. Picking a language in the top bar is remembered
// and wins from then on.
//
// `redirectToLocale` is stringified into an inline <script> in every page's
// <head> (see config.mjs), so it runs before anything is painted and the
// page never flashes the wrong language. It must stay self-contained: no
// imports, no outer variables. `w` is the window (a stand-in in tests).

/** localStorage key holding the language picked in the top bar. */
export const STORAGE_KEY = 'downtify-docs-locale'

/**
 * Sends an English page to its translation: the language picked in the
 * top bar, else the first of the browser's languages the docs are
 * translated into. A tag matches a locale code exactly (ignoring case)
 * or by its first subtag (`es-MX` → `es`, `pt` → `pt-BR`); the first tag
 * that matches anything wins, English included, so `['en', 'de']` stays
 * English. Returns where it went, or `''` when it stayed.
 */
export function redirectToLocale(codes, base, w) {
  w = w || window
  try {
    var path = w.location.pathname
    if (path.indexOf(base) !== 0) return ''
    var rest = path.slice(base.length)
    // Already in a translated folder: stay.
    for (var i = 0; i < codes.length; i++) {
      if (rest === codes[i] || rest.indexOf(codes[i] + '/') === 0) return ''
    }
    var want = ''
    try {
      want = w.localStorage.getItem('downtify-docs-locale') || ''
    } catch (e) {}
    if (want !== 'en' && codes.indexOf(want) < 0) {
      want = ''
      var langs = w.navigator.languages || [w.navigator.language]
      for (var j = 0; j < langs.length && !want; j++) {
        var tag = String(langs[j]).toLowerCase()
        var primary = tag.split('-')[0]
        for (var k = 0; k < codes.length && !want; k++) {
          if (codes[k].toLowerCase() === tag) want = codes[k]
        }
        for (var m = 0; m < codes.length && !want; m++) {
          if (codes[m].toLowerCase().split('-')[0] === primary) want = codes[m]
        }
        if (!want && primary === 'en') want = 'en'
      }
    }
    if (!want || want === 'en') return ''
    var target = base + want + '/' + rest + w.location.search + w.location.hash
    w.location.replace(target)
    return target
  } catch (e) {
    return ''
  }
}
