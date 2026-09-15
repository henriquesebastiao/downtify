// Shared grouping helpers for the "play/filter by playlist, artist or
// album" selector used by both the Player and Library pages. Both pages
// fetch the same `/tracks` (file + artist + album) and `/playlists`
// (M3U-derived) data and just render it differently, so the bucketing
// logic lives here once.

/**
 * Bucket `tracks` (as returned by `GET /tracks`) by the given tag field
 * ('artist' or 'album') into filterable groups. Tracks with no value for
 * that field aren't a member of any group — an untagged file is still
 * reachable via "All Songs", it just isn't a filter target itself.
 */
export function buildGroups(tracks, field) {
  const map = new Map()
  for (const tr of tracks) {
    const name = (tr[field] || '').trim()
    if (!name) continue
    if (!map.has(name)) map.set(name, [])
    map.get(name).push(tr.file)
  }
  return Array.from(map.entries())
    .map(([name, groupFiles]) => ({
      name,
      files: groupFiles,
      count: groupFiles.length,
    }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

/**
 * Resolve the file list for a selector value, where `group` is either
 * `null` (all files) or `{ type: 'playlist' | 'artist' | 'album', name }`.
 */
export function filesForGroup(
  group,
  { files, playlists, artistGroups, albumGroups }
) {
  if (!group) return files
  const groups =
    group.type === 'playlist'
      ? playlists
      : group.type === 'artist'
        ? artistGroups
        : albumGroups
  const match = groups.find((g) => g.name === group.name)
  return match ? match.files : files
}

/**
 * Match an already-loaded file list back to whichever group it came
 * from (playlist, artist or album), so a selector can reflect a
 * selection restored from elsewhere (e.g. the player resuming its
 * last queue) instead of always resetting to "All Songs".
 */
export function detectGroup(
  currentFiles,
  { playlists, artistGroups, albumGroups }
) {
  if (currentFiles.length === 0) return null
  const sources = [
    ['playlist', playlists],
    ['artist', artistGroups],
    ['album', albumGroups],
  ]
  for (const [type, groups] of sources) {
    const match = groups.find(
      (g) =>
        g.files.length === currentFiles.length &&
        g.files.every((f, i) => f === currentFiles[i])
    )
    if (match) return { type, name: match.name }
  }
  return null
}
