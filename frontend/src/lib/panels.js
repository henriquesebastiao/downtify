// Which side panels the Now playing view offers. Pure, so the choices
// a preference changes are unit-testable without mounting the view.

/** Every panel, in tab order. */
export const PANEL_IDS = ['lyrics', 'queue', 'details', 'equalizer']

/**
 * The panels on offer: the lyrics one only while lyrics are shown, and
 * never for a podcast episode — Downtify has no lyrics source for
 * those, so the tab would only ever show "no lyrics for this track".
 */
export function availablePanels({ lyrics = true, isPodcast = false } = {}) {
  return PANEL_IDS.filter((id) => id !== 'lyrics' || (lyrics && !isPodcast))
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
export function defaultPanel({ lyrics = true, isPodcast = false } = {}) {
  // Without lyrics the queue is the most useful thing to have beside the
  // artwork, and it already hides the "Up next" column so it isn't twice.
  return lyrics && !isPodcast ? 'lyrics' : 'queue'
}
