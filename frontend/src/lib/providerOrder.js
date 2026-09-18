// Ordered, individually switchable provider lists (audio sources, lyrics
// providers). The enabled ones are tried top to bottom; the rest sit
// below, switched off.

/**
 * Rows to render: enabled providers in order (position 1..n), then the
 * disabled ones. `info` maps an id to anything extra (title, hint).
 */
export function providerRows(all, enabled, info = {}) {
  const on = enabled.filter((id) => all.includes(id))
  return [
    ...on.map((id, i) => ({ id, enabled: true, position: i + 1, ...info[id] })),
    ...all
      .filter((id) => !on.includes(id))
      .map((id) => ({ id, enabled: false, position: 0, ...info[id] })),
  ]
}

/**
 * Switch a provider on (appended, or first when `first` is true) or off.
 * Returns null when the change isn't allowed — turning the last one off,
 * unless `allowEmpty`.
 */
export function toggleProvider(
  enabled,
  id,
  on,
  { first = false, allowEmpty = false } = {}
) {
  const rest = enabled.filter((item) => item !== id)
  if (!on) return rest.length || allowEmpty ? rest : null
  if (enabled.includes(id)) return null
  return first ? [id, ...rest] : [...rest, id]
}

/** Move a provider up (-1) or down (+1) among the enabled ones. */
export function moveProvider(enabled, id, delta) {
  const next = enabled.slice()
  const from = next.indexOf(id)
  const to = from + delta
  if (from < 0 || to < 0 || to >= next.length) return null
  ;[next[from], next[to]] = [next[to], next[from]]
  return next
}

/** Drag `id` to the slot another enabled provider currently holds. */
export function dropProvider(enabled, id, targetId) {
  if (id === targetId) return null
  const from = enabled.indexOf(id)
  const to = enabled.indexOf(targetId)
  if (from < 0 || to < 0) return null
  const next = enabled.slice()
  next.splice(from, 1)
  next.splice(to, 0, id)
  return next
}
