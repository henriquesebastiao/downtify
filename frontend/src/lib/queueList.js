// Queue list layout: row estimates for the window virtualizer.
// Compact queued/done rows are a 40px tile + py-2 + 8px gap.

export const QUEUE_ROW_GAP = 8

/** Estimated row height including the gap below it. */
export function queueRowEstimate(state) {
  if (state === 'failed') return 148
  if (state === 'active') return 104
  return 56 + QUEUE_ROW_GAP
}
