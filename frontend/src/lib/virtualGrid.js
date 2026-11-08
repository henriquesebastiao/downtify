// Row maths for VirtualGrid: the Library's album/artist grids lay out
// thousands of tiles, and only the rows on screen are rendered.

/**
 * Grid columns at a window width - must match VirtualGrid's grid-cols
 * classes (Tailwind's default breakpoints, plus the 1900px step).
 */
export function columnsFor(width) {
  const w = Number(width) || 0
  if (w >= 1900) return 7
  if (w >= 1536) return 6
  if (w >= 1024) return 5
  if (w >= 768) return 4
  if (w >= 640) return 3
  return 2
}

/** Horizontal gap between tiles (gap-x-4, xs:gap-x-5), in px. */
export function columnGap(width) {
  return (Number(width) || 0) >= 400 ? 20 : 16
}

/** Space under each grid row (the old gap-y-7), in px. */
export const ROW_GAP = 28

/** Title and subtitle under a square cover, in px. */
const TILE_TEXT = 52

/**
 * First guess at a grid row's height before it is measured: a square
 * cover as wide as one column, its text, and the gap under the row.
 */
export function estimateRowHeight(containerWidth, columns, windowWidth) {
  const cols = Math.max(1, columns)
  const gap = columnGap(windowWidth)
  const tile = Math.max(0, (containerWidth - gap * (cols - 1)) / cols)
  return Math.round(tile + TILE_TEXT + ROW_GAP)
}

/** The items of row *index* when rows hold *columns* items. */
export function rowItems(items, index, columns) {
  const cols = Math.max(1, columns)
  return items.slice(index * cols, (index + 1) * cols)
}
