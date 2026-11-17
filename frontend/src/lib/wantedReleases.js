// The Wanted tab (GET /api/monitor/wanted): what every watched artist is
// still missing, its filters and how a Check all / Download all job reads.

import { fold } from '/src/lib/library'

// The release types of the type filter, in display order; a release's
// `section` says which it is.
export const TYPES = ['album', 'ep', 'single', 'mixtape', 'other']

function isUnchecked(entry) {
  return (entry.missing?.unread || 0) > 0
}

// Narrow the artists to a search box and a type. The query matches an
// artist's name (every release stays) or a release's name; the type
// matches a release's section. An artist left with no releases is
// dropped, unless it is not checked yet (it still has something to say).
export function filterWanted(artists, { query = '', type = '' } = {}) {
  const needle = fold(query).trim()
  const out = []
  for (const entry of artists) {
    const byArtist = !needle || fold(entry.watch?.name).includes(needle)
    let releases = entry.releases || []
    if (!byArtist) {
      releases = releases.filter((r) => fold(r.name).includes(needle))
    }
    const matched = byArtist || releases.length > 0
    if (type) releases = releases.filter((r) => r.section === type)
    if (matched && (releases.length || isUnchecked(entry))) {
      out.push(
        releases.length === (entry.releases || []).length
          ? entry
          : { ...entry, releases }
      )
    }
  }
  return out
}

// The numbers of the summary line.
export function summary(totals) {
  return {
    tracks: totals?.tracks || 0,
    releases: totals?.releases || 0,
    unchecked: totals?.unchecked || 0,
  }
}

// Names of the artists whose releases have not been read yet.
export function uncheckedNames(artists) {
  return artists.filter(isUnchecked).map((entry) => entry.watch.name)
}

// The job line: its progress while it runs, then how it ended. `t` is the
// i18n function.
export function jobText(job, t) {
  if (!job) return ''
  if (job.running) {
    return t(
      job.kind === 'download'
        ? 'monitor.wantedDownloading'
        : 'monitor.wantedChecking',
      { done: job.done || 0, total: job.total || 0, name: job.current || '' }
    )
  }
  const parts = [t('monitor.wantedFinished', { done: job.done || 0 })]
  if (job.failed) parts.push(t('monitor.wantedFailed', { count: job.failed }))
  if (job.skipped) {
    parts.push(t('monitor.wantedSkipped', { count: job.skipped }))
  }
  if (job.stopped) parts.push(t('monitor.wantedStopped'))
  return parts.join(' · ')
}
