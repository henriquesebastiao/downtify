// What each audio source did for a failed download (`item.sources`, see
// `downloader.source_attempts` on the server): one row per source tried,
// in order, as `{ provider, result, reason, detail }`.

const LABELS = {
  slskd: 'slskd',
  deemix: 'Deemix',
  'youtube-music': 'YouTube Music',
  youtube: 'YouTube',
  soundcloud: 'SoundCloud',
}

export function sourceLabel(provider) {
  return LABELS[provider] || String(provider || '')
}

/** The source rows of *item* (an empty list when it has none). */
export function attemptsOf(item) {
  const list = item?.sources
  return Array.isArray(list) ? list.filter((a) => a && a.provider) : []
}

/**
 * The short "why" of one attempt, through *t*: slskd's reasons reuse the
 * "Why slskd wasn't used" wording; a failed fetch shows its error.
 */
export function attemptReason(attempt, t) {
  const { provider, result, reason, detail } = attempt
  if (result === 'failed') return t('queue.sourceFailed')
  if (result === 'rejected') return t('queue.sourceRejected')
  if (result === 'skipped') return t('queue.sourceSkipped')
  if (provider === 'slskd' && reason) {
    return t(`slskdMisses.reason.${reason}`)
  }
  return detail ? t('queue.sourceNothingBecause') : t('queue.sourceNothing')
}

/**
 * Failed items counted per source, then per reason, most first:
 * `[{ provider, label, count, reasons: [{ text, count }] }]`. A song
 * that never reached a source counts under `none`.
 */
export function failureBreakdown(items, t) {
  const sources = new Map()
  for (const item of items) {
    const attempts = attemptsOf(item)
    const rows = attempts.length
      ? attempts
      : [{ provider: 'none', result: 'unknown' }]
    for (const attempt of rows) {
      const key = attempt.provider
      if (!sources.has(key)) {
        sources.set(key, {
          provider: key,
          label:
            key === 'none' ? t('queue.sourceNotRecorded') : sourceLabel(key),
          count: 0,
          reasons: new Map(),
        })
      }
      const entry = sources.get(key)
      entry.count += 1
      const text =
        key === 'none'
          ? t('queue.sourceNotRecordedHint')
          : attemptReason(attempt, t) +
            (attempt.result === 'failed' && attempt.detail
              ? `: ${shortError(attempt.detail)}`
              : '')
      entry.reasons.set(text, (entry.reasons.get(text) || 0) + 1)
    }
  }
  return [...sources.values()]
    .map((entry) => ({
      ...entry,
      reasons: [...entry.reasons.entries()]
        .map(([text, count]) => ({ text, count }))
        .sort((a, b) => b.count - a.count),
    }))
    .sort((a, b) => b.count - a.count)
}

/**
 * An error message without what differs per song, so the same failure
 * groups together: yt-dlp's "ERROR: [youtube] <id>: " prefix goes, and
 * the text is cut to its first sentence.
 */
export function shortError(detail) {
  let text = String(detail || '')
    .replace(/^Error:\s*/i, '')
    .replace(/^ERROR:\s*/, '')
    .replace(/^\[[^\]]+\]\s*[\w-]{6,}:\s*/, '')
    .trim()
  const stop = text.search(/[.!?](\s|$)/)
  if (stop > 0) text = text.slice(0, stop + 1)
  return text.length > 140 ? `${text.slice(0, 139)}…` : text
}
