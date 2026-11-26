// The low-bitrate report (downtify/low_bitrate.py): files under a
// bitrate and the Soulseek copies offered for them. Pure, so it's
// unit-testable; the page is views/LowBitrateView.vue.

/** The bitrates the report can list files under (kbps). */
export const THRESHOLDS = [128, 160, 192, 256, 320]
export const DEFAULT_THRESHOLD = 256

/** Replacement states that are still working. */
export const ACTIVE = new Set(['queued', 'downloading', 'replacing'])

/** Error codes the page has words for (lowBitrate.errors.<code>). */
export const ERROR_CODES = new Set([
  'slskd_off',
  'slskd_unreachable',
  'no_tags',
  'search_failed',
  'search_again',
  'missing',
  'already_running',
  'trash_off',
  'trash_refused',
  'enqueue_failed',
  'transfer_failed',
  'tag_mismatch',
  'unreadable',
  'length_mismatch',
  'not_better',
  'target_exists',
  'write_failed',
  'cancelled',
  'dedupe_replacement_pending',
  'dedupe_missing',
  'dedupe_invalid',
  'failed',
])

/** The i18n key for an error code (unknown codes read as "failed"). */
export function errorKey(code) {
  return `lowBitrate.errors.${ERROR_CODES.has(code) ? code : 'failed'}`
}

/** Providers the page names (lowBitrate.sources.<name>). */
const SOURCES = new Set([
  'youtube',
  'youtube-music',
  'soundcloud',
  'slskd',
  'deemix',
  'folder',
])

/** The i18n key for where a file came from, or '' when unknown. */
export function sourceKey(source) {
  return SOURCES.has(source) ? `lowBitrate.sources.${source}` : ''
}

/** What a replacement row is doing: 'working', 'done', 'error' or ''. */
export function replacementPhase(replacement) {
  if (!replacement) return ''
  if (ACTIVE.has(replacement.state)) return 'working'
  return replacement.state === 'done' ? 'done' : 'error'
}

/** Whether a file's search is still running. */
export function searching(track) {
  return ['queued', 'searching'].includes(track?.search?.state)
}

/** The candidates a search found (none while it runs or failed). */
export function candidatesOf(track) {
  return track?.search?.state === 'done' ? track.search.candidates || [] : []
}

/** The candidate picked for a track: the one chosen, else the first
 * (the best by the report's order), else ''. */
export function choiceFor(track, choices) {
  const found = candidatesOf(track)
  const chosen = choices?.[track.file]
  if (chosen && found.some((c) => c.id === chosen)) return chosen
  return found[0]?.id || ''
}

/** Whether a track can be replaced now: a copy found, nothing running. */
export function canReplace(track) {
  return (
    candidatesOf(track).length > 0 &&
    replacementPhase(track.replacement) !== 'working'
  )
}

/** Whether a track can be searched now. */
export function canSearch(track) {
  return !searching(track) && replacementPhase(track.replacement) !== 'working'
}

/** The replace request for the selected tracks that have a copy. */
export function replaceItems(tracks, selected, choices) {
  const wanted = new Set(selected)
  return tracks
    .filter((track) => wanted.has(track.file) && canReplace(track))
    .map((track) => ({
      file: track.file,
      candidate: choiceFor(track, choices),
    }))
}

/** "320 kbps MP3", "VBR ~245 kbps MP3", "MP3" (no bitrate listed). */
export function qualityLabel(candidate, t) {
  const format = String(candidate.format || '').toUpperCase()
  if (!candidate.bitrate) return t('lowBitrate.noBitrate', { format })
  return t(candidate.vbr ? 'lowBitrate.qualityVbr' : 'lowBitrate.quality', {
    kbps: candidate.bitrate,
    format,
  })
}

/** Whether anything on the page is still working (poll while it is). */
export function anyWorking(report) {
  return (report?.tracks || []).some(
    (track) =>
      searching(track) || replacementPhase(track.replacement) === 'working'
  )
}
