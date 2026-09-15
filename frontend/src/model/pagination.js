function range(start, end) {
  if (end < start) return []
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

/**
 * Build a condensed pagination sequence, e.g.
 * `[1, 2, 3, 'ellipsis', 19, 20, 21, 'ellipsis', 36, 37, 38]` for
 * `paginationItems(20, 38)` — always the first/last `boundaryCount`
 * pages, always a `siblingCount`-wide window around the current page,
 * and a single `'ellipsis'` marker wherever two kept pages aren't
 * actually adjacent numbers. Showing every page number (as the
 * Library/Search/Queue lists used to) is impractical once there are
 * more than a handful of pages, especially on mobile.
 *
 * Groups that already overlap or touch (e.g. the current page near
 * page 1) merge into one contiguous run with no ellipsis between them
 * — see the `current` near either end in the tests.
 */
export function paginationItems(
  current,
  total,
  { boundaryCount = 3, siblingCount = 1 } = {}
) {
  if (total <= 0) return []

  const startBoundary = range(1, Math.min(boundaryCount, total))
  const endBoundary = range(Math.max(total - boundaryCount + 1, 1), total)
  const siblings = range(
    Math.max(current - siblingCount, 1),
    Math.min(current + siblingCount, total)
  )

  const kept = [
    ...new Set([...startBoundary, ...siblings, ...endBoundary]),
  ].sort((a, b) => a - b)

  const items = []
  for (let i = 0; i < kept.length; i++) {
    if (i > 0 && kept[i] - kept[i - 1] > 1) {
      items.push('ellipsis')
    }
    items.push(kept[i])
  }
  return items
}

/**
 * A pagination sequence guaranteed to fit a single row on a phone-width
 * screen, however many pages there are — the default `paginationItems`
 * config can still produce 9+ buttons (e.g. two boundaries, a sibling
 * window and two ellipses), which wraps onto a second line on mobile.
 *
 * Whenever the default sequence is already short — which, thanks to
 * `paginationItems`' overlap-merging, is exactly when there's little or
 * nothing condensed about it yet (few total pages) — it's reused as-is,
 * so a small book of pages stays just as informative on mobile as on
 * desktop. Only once it's genuinely long does this fall back to a much
 * tighter first/current/last window.
 */
export function mobilePaginationItems(current, total, inlineThreshold = 8) {
  const full = paginationItems(current, total)
  if (full.length <= inlineThreshold) return full
  return paginationItems(current, total, {
    boundaryCount: 1,
    siblingCount: 0,
  })
}
