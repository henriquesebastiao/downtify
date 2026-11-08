// The Monitor page's artist suggestions (GET /api/monitor/artist-suggestions):
// each list's pages, put together as "Show more" loads them. Pure (no API
// client import), like paths.js.

/** A list with nothing loaded yet. */
export function emptySuggestionPage() {
  return { items: [], total: 0, next_offset: null }
}

/**
 * `next` (the page after `current`) added below `current`. An artist already
 * shown isn't repeated: a list can shift between two requests (a listen
 * counted meanwhile), bringing a name back on the next page.
 */
export function appendSuggestionPage(current, next) {
  const shown = new Set(current.items.map((row) => row.name))
  return {
    ...next,
    items: [
      ...current.items,
      ...next.items.filter((row) => !shown.has(row.name)),
    ],
  }
}
