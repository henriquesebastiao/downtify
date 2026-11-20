// "Why slskd wasn't used" (GET /api/slskd/misses): the reasons downloads
// fell through from slskd to another source, as bars.

// Every reason the server reports, in the order a download gets further
// (downtify/slskd_provider.py MISS_REASONS), plus `unknown`.
export const MISS_REASONS = [
  'not_configured',
  'unreachable',
  'search_failed',
  'search_timeout',
  'no_results',
  'no_match',
  'low_confidence',
  'quality_filtered',
  'timeout',
  'transfer_failed',
  'tag_mismatch',
  'unknown',
]

/** A recorded reason as the panel lists it. */
export function reasonOf(row) {
  return MISS_REASONS.includes(row?.reason) ? row.reason : 'unknown'
}

/** `[{ reason, count, share }]`, most frequent first; `share` is of the
 * largest, for the bar's width. Unknown reasons read as `unknown`. */
export function missRows(summary) {
  const counts = new Map()
  for (const row of summary?.reasons || []) {
    const reason = reasonOf(row)
    counts.set(reason, (counts.get(reason) || 0) + (Number(row.count) || 0))
  }
  const rows = [...counts]
    .map(([reason, count]) => ({ reason, count }))
    .sort((a, b) => b.count - a.count)
  const top = Math.max(1, ...rows.map((row) => row.count))
  return rows.map((row) => ({ ...row, share: row.count / top }))
}

/** `[{ source, count }]` of what was used instead, most first. */
export function fallbackRows(summary) {
  return Object.entries(summary?.fallbacks || {})
    .map(([source, count]) => ({ source, count: Number(count) || 0 }))
    .sort((a, b) => b.count - a.count)
}
