/** Page numbers with ``'…'`` gaps for compact pagination controls. */

export function paginationRange(current, total) {
  if (total < 1) return []
  if (total === 1) return [1]

  const delta = 2
  const pages = new Set([1, total])
  for (let page = current - delta; page <= current + delta; page += 1) {
    if (page >= 1 && page <= total) pages.add(page)
  }

  const sorted = [...pages].sort((a, b) => a - b)
  const result = []
  let previous = 0
  for (const page of sorted) {
    if (previous && page - previous > 1) result.push('…')
    result.push(page)
    previous = page
  }
  return result
}
