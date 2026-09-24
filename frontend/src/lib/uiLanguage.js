// Telling the server which language the page is shown in. The choice lives in
// the browser (see i18n/index.js), and the server needs it for work that runs
// without one - see `ui_language` in downtify/api.py. Pure, so it's
// unit-testable.

/**
 * Whether the server's saved language is out of date with the one shown.
 * Nothing to send when there is no language to send.
 */
export function needsLanguageSync(saved, current) {
  return !!current && saved !== current
}

/**
 * The server's settings, with `ui_language` set apart from the rest: the
 * settings page edits and saves everything *but* it (it is the page's own
 * language, not a form field, and saving the whole form must never put a
 * stale one back).
 */
export function splitUiLanguage(data) {
  const { ui_language: language, ...rest } = data || {}
  return { uiLanguage: typeof language === 'string' ? language : '', rest }
}
