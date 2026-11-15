// An artist watch's catalogue on its page (GET
// /api/monitor/playlists/{id}/releases): sections, filters and how each
// release's state reads.

// Listed in this order, each under its own heading.
export const SECTIONS = ['album', 'mixtape', 'ep', 'single', 'other']

// Filter chips, in order; `all` shows every release a user can act on
// (not guest spots and bootlegs, which have their own chip).
export const FILTERS = [
  'all',
  'missing',
  'partly',
  'complete',
  'not_watched',
  'off',
  'not_own',
]

// Badge tone of each state.
const TONES = {
  complete: 'accent',
  partly: 'warn',
  missing: 'neutral',
  skipped: 'neutral',
  not_watched: 'neutral',
  off: 'neutral',
  not_own: 'neutral',
}

export function stateTone(state) {
  return TONES[state] || 'neutral'
}

// Whether a release is downloaded by the watch: its switch.
export function isOn(release) {
  return ['complete', 'partly', 'missing'].includes(release.state)
}

// Whether a release has a switch at all (guest spots and bootlegs never
// download).
export function canSwitch(release) {
  return release.state !== 'not_own'
}

export function matchesFilter(release, filter) {
  if (filter === 'all') return release.state !== 'not_own'
  if (filter === 'not_watched') {
    return release.state === 'not_watched' || release.state === 'skipped'
  }
  return release.state === filter
}

// How many releases each chip shows.
export function filterCounts(releases) {
  const counts = Object.fromEntries(FILTERS.map((f) => [f, 0]))
  for (const release of releases) {
    for (const filter of FILTERS) {
      if (matchesFilter(release, filter)) counts[filter] += 1
    }
  }
  return counts
}

// `[{ id, releases }]` per section, newest first, empty ones left out.
export function sectioned(releases, filter = 'all') {
  const shown = releases.filter((r) => matchesFilter(r, filter))
  return SECTIONS.map((id) => ({
    id,
    releases: shown
      .filter(
        (r) => (SECTIONS.includes(r.section) ? r.section : 'album') === id
      )
      .sort((a, b) => String(b.year || '').localeCompare(String(a.year || ''))),
  })).filter((section) => section.releases.length)
}

// Display names of the catalogues a release is listed by.
const SOURCE_NAMES = {
  youtube: 'YouTube Music',
  'youtube-music': 'YouTube Music',
  deezer: 'Deezer',
  musicbrainz: 'MusicBrainz',
}

export function sourceNames(release) {
  return (release.sources || []).map((s) => SOURCE_NAMES[s] || s).join(', ')
}
