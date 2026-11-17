// The watches picked on the Monitor page to change together. A selection
// is a Set of watch ids; each helper returns a new Set.

/**
 * Click on a watch's box. With `range` (Shift held) every watch shown
 * between the last one clicked (`anchor`) and this one takes the state
 * this one is switched to.
 */
export function toggleWatch(selected, visibleIds, id, { anchor, range } = {}) {
  const next = new Set(selected)
  const on = !selected.has(id)
  const from = range && anchor != null ? visibleIds.indexOf(anchor) : -1
  const to = visibleIds.indexOf(id)
  if (from === -1 || to === -1) {
    if (on) next.add(id)
    else next.delete(id)
    return next
  }
  const [start, end] = from < to ? [from, to] : [to, from]
  for (const each of visibleIds.slice(start, end + 1)) {
    if (on) next.add(each)
    else next.delete(each)
  }
  return next
}

/** 'all', 'some' or 'none' of the watches shown are picked. */
export function shownState(selected, visibleIds) {
  const picked = visibleIds.filter((id) => selected.has(id)).length
  if (!picked) return 'none'
  return picked === visibleIds.length ? 'all' : 'some'
}

/** The box above the list: picks every watch shown, or, when they all
 * are, unpicks them (watches hidden by the filter keep their state). */
export function toggleShown(selected, visibleIds) {
  const next = new Set(selected)
  if (shownState(selected, visibleIds) === 'all') {
    for (const id of visibleIds) next.delete(id)
  } else {
    for (const id of visibleIds) next.add(id)
  }
  return next
}

/** Drops ids no longer in the tab (a watch stopped, or the list reloaded). */
export function keepExisting(selected, ids) {
  const present = new Set(ids)
  const next = new Set([...selected].filter((id) => present.has(id)))
  return next.size === selected.size ? selected : next
}
