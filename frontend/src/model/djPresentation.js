// Derive the audible decks from media time, never from the render head.
export function djPresentation(session, position) {
  const rows = session?.timeline || []
  let index = rows.findIndex(
    (row) => row.start <= position && position < row.end
  )
  if (index < 0) index = position < (rows[0]?.start ?? 0) ? 0 : rows.length - 1
  const row = rows[index]
  const next = rows[index + 1]
  const track = (value) =>
    value && session.tracks?.find((item) => item.id === value.id)
  const overlap = next ? row.end - next.start : 0
  const progress =
    overlap > 0 && position >= next.start && position < row.end
      ? Math.max(0, Math.min(1, (position - next.start) / overlap))
      : null
  return {
    current: track(row),
    next: track(next),
    row,
    nextRow: next,
    transition: progress,
    elapsed: row ? Math.max(0, position - row.start) : 0,
    duration: row ? row.end - row.start : 0,
  }
}

export function djResumePoint(session, position) {
  const state = djPresentation(session, position)
  const row =
    state.transition !== null && state.transition >= 0.5
      ? state.nextRow
      : state.row
  const track = row && session.tracks?.find((item) => item.id === row.id)
  if (!track?.file) return null
  return {
    file: track.file,
    id: row.id,
    occurrence: row.occurrence ?? session.timeline.indexOf(row),
    seconds: Math.max(
      0,
      (row.cue || 0) + (position - row.start) * (row.speed || 1)
    ),
  }
}
