// Turns the answer of POST /api/{slskd,navidrome}/test into the lines the
// Settings page shows. Pure, so the mapping is unit-testable and the
// component only has to translate and draw what this returns.

/**
 * Every `<check id>_<code>` the backend can report. A code the UI doesn't
 * know (a newer backend) is shown generically rather than as a raw key.
 */
export const KNOWN_CODES = new Set([
  'config_missing',
  'connection_unreachable',
  'connection_timeout',
  'connection_bad_url',
  'connection_tls',
  'connection_not_slskd',
  'connection_not_navidrome',
  'connection_http_error',
  'auth_bad_key',
  'auth_bad_credentials',
  'auth_api_error',
  'soulseek_ok',
  'soulseek_offline',
  'folder_ok',
  'folder_missing',
  'scan_ok',
  'scan_not_admin',
  'scan_not_admin_separate',
  'scan_bad_admin',
])

/** Checks that only say "fine" and are folded into "Connected to …". */
const FOLDED = new Set(['connection', 'auth'])

/**
 * `[{ status: 'ok'|'warn'|'fail', key, params }]` for a test answer, in
 * the order to show them. `key` is under `settings.test.` in the locale
 * files. `url` is what was tested, for the messages that name it.
 */
export function describeTest(result, { url = '' } = {}) {
  if (!result) return []
  const lines = []
  if (result.server) {
    lines.push({
      status: 'ok',
      key: 'connected',
      params: { server: result.server },
    })
  }
  for (const check of result.checks || []) {
    if (check.status === 'ok' && FOLDED.has(check.id)) continue
    const code = `${check.id}_${check.code}`
    const known = KNOWN_CODES.has(code)
    lines.push({
      status: check.status,
      key: known ? code : 'unknown',
      params: { url, detail: check.detail || '', code },
    })
  }
  return lines
}

/** True when a test can be started: every required field has a value. */
export function canTest(config, fields) {
  return fields.every((field) => String(config?.[field] ?? '').trim() !== '')
}

export const REQUIRED_FIELDS = {
  slskd: ['base_url', 'api_key'],
  navidrome: ['url', 'username', 'password'],
}
