// Which side panels the Now playing view offers. Pure, so the choices
// a preference changes are unit-testable without mounting the view.

/** Every panel, in tab order. */
export const PANEL_IDS = ['lyrics', 'karaoke', 'queue', 'details', 'equalizer']

/** The panels that only show a track's lyrics, in different layouts. */
const LYRICS_PANELS = ['lyrics', 'karaoke']

/**
 * The panels on offer: the lyrics ones only while lyrics are shown, and
 * never for a podcast episode — Downtify has no lyrics source for
 * those, so the tab would only ever show "no lyrics for this track".
 * A streamed track (not in the library) offers neither lyrics nor
 * details — there is no file behind either tab.
 */
export function availablePanels({
  lyrics = true,
  isPodcast = false,
  isStream = false,
} = {}) {
  return PANEL_IDS.filter(
    (id) =>
      (!LYRICS_PANELS.includes(id) || (lyrics && !isPodcast && !isStream)) &&
      (id !== 'details' || !isStream)
  )
}

/**
 * The `?panel=` someone asked for, or `''` when it isn't on offer — a
 * link to the lyrics panel keeps working after lyrics are turned off, it
 * just lands on the default instead of an empty tab.
 */
export function requestedPanel(value, available) {
  const requested = String(value || '')
  return available.includes(requested) ? requested : ''
}

/** What the side panel shows when none was picked. */
export function defaultPanel({
  lyrics = true,
  isPodcast = false,
  isStream = false,
} = {}) {
  // Without lyrics the queue is the most useful thing to have beside the
  // artwork, and it already hides the "Up next" column so it isn't twice.
  return lyrics && !isPodcast && !isStream ? 'lyrics' : 'queue'
}

/**
 * Whether the panel can sit beside an "Up next" column on wide screens:
 * not when it is the queue itself (it would show twice) or karaoke
 * (the words take the whole screen).
 */
export function canShowUpNextBeside(panel) {
  return panel !== 'queue' && panel !== 'karaoke'
}

/**
 * Whether the "Up next" column shows beside *panel*: when it can, unless
 * the viewer hid it for a bigger view of the words (issue #679).
 */
export function showsUpNextBeside(panel, wanted = true) {
  return canShowUpNextBeside(panel) && wanted !== false
}
