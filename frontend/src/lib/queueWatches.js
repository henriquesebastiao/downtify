// Which Monitor watch each queue item is downloading for. Monitor adds
// `watch` ({id, name, kind, url, source, cover_file}) to the progress
// events of the songs it downloads; the queue keeps it on the item.
import { proxiedArtistPhotoUrl } from './artistPhotoProxy'
import { playlistCoverURL } from './paths'
import { watchCoverUrl } from './watches'

/**
 * A watch's picture: the artist's photo, or the playlist's - the cover
 * saved beside its M3U, else the one its service shows (see
 * `watchCoverUrl`). An event without the watch's id keeps the saved file.
 */
export function watchCover(watch) {
  if (!watch) return ''
  if (watch.kind === 'artist') return proxiedArtistPhotoUrl(watch.name)
  return watchCoverUrl(watch) || playlistCoverURL(watch.cover_file)
}

/**
 * The watches behind *items*, with how many songs each put in the queue
 * (`count`) and how many of those are still waiting or downloading
 * (`waiting`): most songs first, then by name.
 */
export function queueWatches(items) {
  const byId = new Map()
  for (const item of items || []) {
    const watch = item?.watch
    if (!watch || watch.id == null) continue
    let row = byId.get(watch.id)
    if (!row) {
      row = { watch, count: 0, waiting: 0 }
      byId.set(watch.id, row)
    }
    row.watch = watch
    row.count += 1
    if (item.state === 'active' || item.state === 'queued') row.waiting += 1
  }
  return [...byId.values()].sort(
    (a, b) =>
      b.count - a.count ||
      String(a.watch.name || '').localeCompare(String(b.watch.name || ''))
  )
}
