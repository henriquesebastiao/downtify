// Geometry for the mini player's seek bar hover preview.

/** Where `clientX` falls along a rail, as 0–1 (clamped to its ends). */
export function railRatio(clientX, rect) {
  if (!rect || !(rect.width > 0)) return 0
  return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
}

/**
 * Left edge (px, relative to the rail) for a tooltip of `tipWidth`
 * centred over `ratio`, kept within `slack` px past either end of the
 * rail so it never slides off the player.
 */
export function tooltipLeft(ratio, railWidth, tipWidth, slack = 0) {
  const left = ratio * railWidth - tipWidth / 2
  const min = 0 - slack
  const max = railWidth + slack - tipWidth
  return max < min
    ? (railWidth - tipWidth) / 2
    : Math.max(min, Math.min(max, left))
}
