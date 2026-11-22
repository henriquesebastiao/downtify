// AcoustID (identify songs by their sound): what the settings and the
// Library upgrade say about it. Pure, so it is unit-testable.

/** A `GET /api/acoustid` payload with every field present. */
export function normalizeAcoustid(payload) {
  const data = payload || {}
  return {
    enabled: Boolean(data.enabled),
    keySet: Boolean(data.key_set),
    keyHint: String(data.key_hint || ''),
    fingerprinter: String(data.fingerprinter || ''),
    ready: Boolean(data.ready),
  }
}

/**
 * Why identifying by sound can't run yet, as an i18n key under
 * `upgrade.` (`''` when it can): turned off, no key, or no fingerprint
 * tool on the server.
 */
export function acoustidBlocker(status) {
  if (!status.enabled) return 'acoustidOff'
  if (!status.keySet) return 'acoustidNoKey'
  if (!status.fingerprinter) return 'acoustidNoTool'
  return ''
}

/** What makes fingerprints on the server, as an i18n key under `settings.`. */
export function fingerprinterKey(status) {
  if (status.fingerprinter === 'fpcalc') return 'acoustidToolFpcalc'
  if (status.fingerprinter === 'ffmpeg') return 'acoustidToolFfmpeg'
  return 'acoustidToolMissing'
}

/** A key as AcoustID issues them: letters, digits, `-` and `_`. */
export function looksLikeKey(value) {
  return /^[A-Za-z0-9_-]{4,64}$/.test(String(value || '').trim())
}
