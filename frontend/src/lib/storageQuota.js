// Storage quotas (issue #677): what GET /api/me/storage and
// GET /api/users/storage answer, turned into what the pages show.
// Sizes are bytes on the wire and GB (1024³, like formatBytes) on screen.

export const GB = 1024 ** 3
/** A user's own quota meaning "no limit" (`own` / `quota_bytes`). */
export const UNLIMITED = -1

export const MODE_DEFAULT = 'default'
export const MODE_UNLIMITED = 'unlimited'
export const MODE_CUSTOM = 'custom'

/** Bytes as a GB figure for an input: `1.5`, `2`, or `''` for none. */
export function bytesToGb(bytes) {
  const value = Number(bytes)
  if (!Number.isFinite(value) || value <= 0) return ''
  const gb = value / GB
  // Two decimals, or three significant digits below 1 GB (so 4 MB isn't
  // shown as 0).
  return String(
    gb >= 1 ? Math.round(gb * 100) / 100 : Number(gb.toPrecision(3))
  )
}

/** A GB figure typed in an input as bytes; `null` when empty or invalid. */
export function gbToBytes(text) {
  const value = Number(String(text ?? '').replace(',', '.'))
  if (!String(text ?? '').trim() || !Number.isFinite(value) || value <= 0) {
    return null
  }
  return Math.round(value * GB)
}

/** Which choice an account's own setting stands for. */
export function quotaMode(own) {
  if (own === null || own === undefined) return MODE_DEFAULT
  return Number(own) < 0 ? MODE_UNLIMITED : MODE_CUSTOM
}

/** What `PUT /api/users/{id}/storage` takes for a choice: bytes, -1 or
 * null (follow the default); `undefined` when the GB figure is invalid. */
export function quotaPayload(mode, gb) {
  if (mode === MODE_DEFAULT) return null
  if (mode === MODE_UNLIMITED) return UNLIMITED
  const bytes = gbToBytes(gb)
  return bytes === null ? undefined : bytes
}

/** How full a limited account is, 0-100 (0 when unlimited). */
export function quotaPercent(status) {
  if (!status || status.unlimited || !status.limit) return 0
  return Math.min(100, Math.max(0, (status.used / status.limit) * 100))
}

/** `warn` from 90 % on, `danger` once out of space, else `''`. */
export function quotaTone(status) {
  if (!status || status.unlimited) return ''
  if (status.exceeded) return 'danger'
  return quotaPercent(status) >= 90 ? 'warn' : ''
}
