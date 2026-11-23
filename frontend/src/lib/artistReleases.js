// An artist watch's catalogue on its page (GET
// /api/monitor/playlists/{id}/releases): sections, filters and how each
// release's state reads.

// Listed in this order, each under its own heading.
export const SECTIONS = ['album', 'mixtape', 'ep', 'single', 'other']

// The MusicBrainz release kinds a watch can let in (musicbrainz.KINDS),
// in the server's order.
export const MUSICBRAINZ_KINDS = [
  'mixtape',
  'soundtrack',
  'live',
  'compilation',
  'remix',
  'dj-mix',
  'demo',
]

// *kinds* with *kind* switched on or off, in MUSICBRAINZ_KINDS order.
export function toggledKinds(kinds, kind) {
  const on = new Set(kinds || [])
  if (on.has(kind)) on.delete(kind)
  else on.add(kind)
  return MUSICBRAINZ_KINDS.filter((k) => on.has(k))
}

// Filter chips, in order; `all` shows every release a user can act on
// (not guest spots and bootlegs, which have their own chip).
export const FILTERS = [
  'all',
  'missing',
  'upcoming',
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
  upcoming: 'accent',
  skipped: 'neutral',
  not_watched: 'neutral',
  off: 'neutral',
  not_own: 'neutral',
}

export function stateTone(state) {
  return TONES[state] || 'neutral'
}

// Whether the watch downloads a release: its switch. The server says
// (`wanted`) - what the library has of it is another matter (`state`):
// an album owned before the watch started is complete, not watched.
export function isOn(release) {
  if (typeof release.wanted === 'boolean') return release.wanted
  return ['complete', 'partly', 'missing', 'upcoming'].includes(release.state)
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

// When an announced release comes out, as short as the date allows:
// "5 Dec" this year, "5 Dec 2027" another, "Dec 2026" or "2027" when a
// catalogue only gives the month or the year. `''` without a date.
export function comingDate(day, locale = 'en', today = new Date()) {
  const match = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(String(day || ''))
  if (!match) return ''
  const [, year, month, date] = match
  if (!month) return year
  const when = new Date(Number(year), Number(month) - 1, Number(date || 1))
  const options = date
    ? { day: 'numeric', month: 'short' }
    : { month: 'short', year: 'numeric' }
  if (date && Number(year) !== today.getFullYear()) options.year = 'numeric'
  try {
    return new Intl.DateTimeFormat(locale, options).format(when)
  } catch {
    return new Intl.DateTimeFormat('en', options).format(when)
  }
}

// A release's badge text: its state, with what the library has of it or,
// for an announced one, when it comes out.
export function stateLabel(release, t, locale = 'en') {
  if (release.state === 'complete' || release.state === 'partly') {
    return t(`artistReleases.state.${release.state}`, {
      have: release.have,
      total: release.total || '?',
    })
  }
  if (release.state === 'upcoming') {
    const date = comingDate(release.release_date, locale)
    return date
      ? t('artistReleases.state.upcoming', { date })
      : t('artistReleases.state.upcomingNoDate')
  }
  return t(`artistReleases.state.${release.state}`)
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
