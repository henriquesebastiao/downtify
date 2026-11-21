// "What's new" after an update: which version this browser last showed
// the notes for, and whether the running one is newer. Pure (storage is
// passed in), so it's unit-testable - the dialog is
// components/shell/WhatsNewDialog.vue.

export const SEEN_KEY = 'downtify-whats-new-seen'
// Written by model/api.js:getVersion() since long before this dialog
// existed: the version this browser last loaded the app with.
export const LAST_VERSION_KEY = 'version'

export const REPO_URL = 'https://github.com/henriquesebastiao/downtify'

const VERSION_RE = /(\d+)\.(\d+)\.(\d+)/

/** `'3.12.0'` → `[3, 12, 0]`; `null` for anything that isn't one. */
export function parseVersion(raw) {
  const match = VERSION_RE.exec(String(raw ?? ''))
  return match ? match.slice(1).map(Number) : null
}

/** Whether `latest` is a strictly newer version than `current`. */
export function isNewer(latest, current) {
  const a = parseVersion(latest)
  const b = parseVersion(current)
  if (!a || !b) return false
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] > b[i]
  }
  return false
}

/** A real release, not the `0.0.0` the app falls back to offline. */
export function isRelease(version) {
  const parts = parseVersion(version)
  return Boolean(parts) && parts.some((n) => n > 0)
}

export function releaseUrl(version) {
  return `${REPO_URL}/releases/tag/${version}`
}

function read(storage, key) {
  try {
    return storage?.getItem(key) ?? null
  } catch {
    return null
  }
}

function write(storage, key, value) {
  try {
    storage?.setItem(key, value)
  } catch {
    // Private mode, blocked storage: shown again next time, harmless.
  }
}

/**
 * Before the app learns its version: a browser that used Downtify before
 * this dialog existed has no "seen" mark yet, but it does remember the
 * version it last ran. Start from that one, so the first update after
 * this feature shipped is announced too. Runs before getVersion()
 * overwrites it (and reloads the page on a new version).
 */
export function seedSeenVersion(storage) {
  if (read(storage, SEEN_KEY) !== null) return
  const last = read(storage, LAST_VERSION_KEY)
  if (isRelease(last)) write(storage, SEEN_KEY, last)
}

/**
 * Whether to show the notes for `current`. A browser that never ran
 * Downtify (nothing seen, nothing remembered) is a new install, not an
 * update: it is marked as seen and shown nothing.
 */
export function shouldShowWhatsNew(storage, current) {
  if (!isRelease(current)) return false
  const seen = read(storage, SEEN_KEY)
  if (seen === null || !isRelease(seen)) {
    write(storage, SEEN_KEY, current)
    return false
  }
  return isNewer(current, seen)
}

export function markWhatsNewSeen(storage, version) {
  if (isRelease(version)) write(storage, SEEN_KEY, version)
}

/**
 * The highlights of `version` in `locale`, falling back to English, or
 * `[]` when the release has none written (the dialog then only links to
 * the full changelog).
 */
export function highlightsFor(notes, version, locale) {
  const entry = notes?.[version]
  if (!entry) return []
  const list = entry[locale] || entry[String(locale).split('-')[0]] || entry.en
  return Array.isArray(list) ? list : []
}
