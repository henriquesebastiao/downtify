// The Wanted tab (GET /api/monitor/wanted): what every watched artist is
// still missing, its filters and how a Check all / Download all job reads.

import { fold } from '/src/lib/library'

// The release types of the type filter, in display order; a release's
// `section` says which it is.
export const TYPES = ['album', 'ep', 'single', 'mixtape', 'other']

function isUnchecked(entry) {
  return (entry.unchecked || 0) > 0
}

// Narrow the artists to a search box and a type. The query matches an
// artist's name (every release stays) or a release's name; the type
// matches a release's section. An artist left with no releases is
// dropped (the not-checked line names the unchecked ones separately).
export function filterWanted(artists, { query = '', type = '' } = {}) {
  const needle = fold(query).trim()
  const out = []
  for (const entry of artists) {
    const byArtist = !needle || fold(entry.watch?.name).includes(needle)
    let releases = entry.releases || []
    if (!byArtist) {
      releases = releases.filter((r) => fold(r.name).includes(needle))
    }
    if (type) releases = releases.filter((r) => r.section === type)
    if (releases.length) {
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
    uncheckedReleases: totals?.unchecked_releases || 0,
  }
}

// "12 songs missing in 4 releases", in the locale's own word order.
export function summaryText(totals, t) {
  return t('monitor.wantedSummary', {
    songs: t('monitor.wantedSongs', { count: totals.tracks }),
    releases: t('monitor.wantedReleases', { count: totals.releases }),
  })
}

// The releases the tab lists: those read and those not read yet (the
// count on the tab).
export function listedReleases(artists) {
  return artists.reduce((sum, entry) => sum + (entry.releases?.length || 0), 0)
}

// Names of the artists with releases not read yet.
export function uncheckedNames(artists) {
  return artists.filter(isUnchecked).map((entry) => entry.watch.name)
}

// The most names the "not checked yet" line spells out.
export const NAMES_SHOWN = 3

// "Ace, Bee, Cat and 85 more". `t` is the i18n function.
export function namesText(names, t) {
  if (names.length <= NAMES_SHOWN) return names.join(', ')
  const rest = names.length - NAMES_SHOWN
  return `${names.slice(0, NAMES_SHOWN).join(', ')} ${t('monitor.wantedMore', {
    count: rest,
  })}`
}

// The job line: its progress while it runs, then how it ended. `t` is the
// i18n function.
export function jobText(job, t) {
  if (!job) return ''
  if (job.running) {
    if (job.stopping) {
      return job.kind === 'download' && job.current
        ? t('monitor.wantedStoppingDownload', { name: job.current })
        : t('monitor.wantedStoppingCheck')
    }
    const total = job.total || 0
    // The artist being worked on counts: "1 of 87", not "0 of 87".
    const done = Math.min((job.done || 0) + (job.current ? 1 : 0), total)
    return t(
      job.kind === 'download'
        ? 'monitor.wantedDownloading'
        : 'monitor.wantedChecking',
      { done, total, name: job.current || '' }
    )
  }
  const parts = [t('monitor.wantedFinished', { count: job.done || 0 })]
  if (job.failed) parts.push(t('monitor.wantedFailed', { count: job.failed }))
  if (job.skipped) {
    parts.push(t('monitor.wantedSkipped', { count: job.skipped }))
  }
  if (job.stopped) parts.push(t('monitor.wantedStopped'))
  return parts.join(' · ')
}
