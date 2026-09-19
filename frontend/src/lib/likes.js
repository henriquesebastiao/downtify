// Which library files are liked, and what a tap does to that set. Pure,
// so the optimistic update — and undoing just that one tap — is
// unit-testable without a browser.

/** The liked files as a Set, from what the server sent (any junk out). */
export function likedSet(files) {
  return new Set(
    (Array.isArray(files) ? files : []).filter(
      (file) => typeof file === 'string' && file !== ''
    )
  )
}

/** A copy of `liked` with `file` liked (`on`) or not. Never mutates. */
export function withLike(liked, file, on) {
  const next = new Set(liked)
  if (on) next.add(file)
  else next.delete(file)
  return next
}

/**
 * True when a tap is the one that makes the playlist: liking while
 * nothing was liked. The playlist appears with the first like.
 */
export function isFirstLike(before, on) {
  return on && before.size === 0
}
