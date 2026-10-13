// What a song row outside the library shows: the download queue's
// state, the library's, or nothing yet.

/**
 * The badge a search/link/top-songs row shows.
 *
 * [item] is the song's queue row (or null), [inLibrary] whether the
 * library already has it. A finished queue row outlives its file —
 * deleting a track from the library leaves its job "done" — so the
 * `done` state only counts while the song is still there; otherwise
 * the row is offered for download again.
 */
export function songDownloadState(item, inLibrary) {
  const staleDone = item?.state === 'done' && !inLibrary
  if (item && !staleDone) return item.state
  return inLibrary ? 'library' : 'new'
}
