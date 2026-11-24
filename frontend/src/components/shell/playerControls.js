// Which of the mini player's controls fit its bar, and which move into its
// "More controls" menu (issue #552). Pure, so it's unit-testable.
//
// Track info, previous / play / next and the volume always stay. The rest
// give way one at a time, least important first, as the bar narrows:
// the last in this list is the first to go.
export const CONTROL_PRIORITY = [
  'clock',
  'repeat',
  'shuffle',
  'like',
  'nowPlaying',
  'lyrics',
  'library',
  'similar',
  'close',
]

// Widths in px, each with the gap that comes with it, measured from the
// bar's classes (see MiniPlayer.vue) and rounded up: guessing a little
// wide only moves a control into the menu a little early, guessing short
// clips it, which is the bug this fixes.
// The width planned against is the bar's content box (its padding and
// border already taken off by the ResizeObserver).
const DESKTOP = {
  // The gaps between the three sections, the track info at its narrowest
  // and previous / play / next with their gaps.
  base: 40 + 200 + 148,
  more: 36,
  volume: { inline: 124, compact: 36 },
  costs: {
    clock: 112,
    repeat: 52,
    shuffle: 52,
    like: 36,
    nowPlaying: 72,
    lyrics: 36,
    library: 52,
    similar: 52,
    close: 36,
  },
}

const PHONE = {
  base: 24 + 130 + 132,
  more: 36,
  volume: null,
  costs: {
    repeat: 44,
    shuffle: 44,
    like: 36,
    nowPlaying: 0,
    lyrics: 0,
    library: 44,
    similar: 44,
    close: 36,
  },
}

/**
 * Plan the bar for `width` px. `available` lists the optional controls
 * this track has (no lyrics button when lyrics are off, no like on a
 * stream, ...). On a phone there is no volume (the device's buttons do
 * it), no clock (the hairline shows progress), and Now playing and the
 * lyrics are a tap on the track away, so they only ever sit in the menu.
 *
 * Returns `{ shown, overflow, volume }`: the controls on the bar (a Set),
 * the ones in the menu in priority order, and `'inline'` (button and
 * slider), `'compact'` (a button opening the slider) or `'none'`.
 * Without a width yet (0), everything is shown, as before.
 */
export function planControls(width, available, { phone = false } = {}) {
  const spec = phone ? PHONE : DESKTOP
  const offered = CONTROL_PRIORITY.filter(
    (id) => available.includes(id) && id in spec.costs
  )
  let shown = offered.filter((id) => !phone || spec.costs[id] > 0)
  let overflow = offered.filter((id) => !shown.includes(id))
  let volume = spec.volume ? 'inline' : 'none'
  if (!width) return { shown: new Set(offered), overflow: [], volume }

  const needed = () =>
    spec.base +
    (spec.volume ? spec.volume[volume] : 0) +
    shown.reduce((sum, id) => sum + spec.costs[id], 0) +
    (overflow.length ? spec.more : 0)

  while (shown.length && needed() > width) {
    const dropped = shown[shown.length - 1]
    shown = shown.slice(0, -1)
    overflow = CONTROL_PRIORITY.filter(
      (id) => id === dropped || overflow.includes(id)
    )
  }
  if (volume === 'inline' && needed() > width) volume = 'compact'
  return { shown: new Set(shown), overflow, volume }
}
