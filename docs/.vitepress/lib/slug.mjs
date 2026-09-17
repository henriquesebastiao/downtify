// Heading ids, compatible with the ones the docs had under zensical
// (Python-Markdown's `toc` extension), so existing deep links keep
// working: ASCII-folded, punctuation dropped, whitespace/dashes collapsed
// to '-', and repeats numbered `_1`, `_2`, ...

/** Python-Markdown `toc.slugify(value, '-')`. */
export function slugify(text) {
  return String(text)
    .normalize('NFKD')
    .replace(/[^\x00-\x7f]/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, '-')
}

/** Python-Markdown `toc.unique(id, ids)`; records the id in `used`. */
export function unique(id, used) {
  while (used.has(id) || !id) {
    const match = /^(.*)_([0-9]+)$/.exec(id)
    id = match ? `${match[1]}_${Number(match[2]) + 1}` : `${id}_1`
  }
  used.add(id)
  return id
}

const seen = new WeakMap()

/** `markdown-it-anchor` `slugifyWithState`: ids are unique per page. */
export function slugifyWithState(text, state) {
  let used = seen.get(state.env)
  if (!used) {
    used = new Set()
    seen.set(state.env, used)
  }
  return unique(slugify(text), used)
}
