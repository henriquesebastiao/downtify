// Queue tab auto-focus: when to jump to "In progress". Pure, so it's
// unit-testable.

/**
 * Whether the Queue view should jump to the "active" tab. Only when
 * downloads start from idle - not on every bump of the active count, so
 * finishing one item and starting the next doesn't yank the viewer back
 * off the tab they're reading.
 */
export function shouldJumpToActive(activeNow, activeBefore, currentTab) {
  const before = activeBefore ?? 0
  return before === 0 && activeNow > 0 && currentTab !== 'active'
}
