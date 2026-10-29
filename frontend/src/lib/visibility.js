// What admins hide from users (downtify/library_visibility.py): the items
// the API takes, what a menu or selection offers, and the local update
// that follows a change. Pure, so it's unit-testable.

import { albumKey, artistKey, groupingArtistName } from './library'

/** The API item for one track, album or artist. */
export function trackItem(track) {
  return { kind: 'track', file: track.file }
}

export function albumItem(album) {
  return { kind: 'album', artist: album.artist, title: album.title }
}

export function artistItem(artist) {
  return { kind: 'artist', name: artist.name }
}

// Wider rules win, as on the server.
const RANK = { '': 0, track: 1, album: 2, artist: 3 }

/**
 * What an admin may do with a track, album or artist (`hiddenBy` is
 * '', 'track', 'album' or 'artist'; `own` is the kind of rule that item
 * is toggled by): 'hide' when users see it, 'show' when its own rule
 * hides it, `null` when a wider rule does (show that one instead).
 */
export function visibilityAction(hiddenBy, own) {
  if (!hiddenBy) return 'hide'
  return hiddenBy === own ? 'show' : null
}

/**
 * The items a selection of tracks hides and shows:
 * `{ hide: [item], show: [item] }`. A track hidden through its album or
 * artist is left alone - that one is shown from the album or artist.
 */
export function selectionChanges(tracks) {
  const hide = []
  const show = []
  for (const track of tracks) {
    const action = visibilityAction(track.hiddenBy, 'track')
    if (action === 'hide') hide.push(trackItem(track))
    else if (action === 'show') show.push(trackItem(track))
  }
  return { hide, show }
}

function matches(track, item) {
  if (item.kind === 'track') return track.file === item.file
  const artist = groupingArtistName(track)
  if (item.kind === 'album') {
    // The album as the Library groups it (a compilation by "Various
    // Artists"), or as rules made before that keyed it.
    const key = albumKey(item.artist, item.title)
    return (
      Boolean(track.album) &&
      (albumKey(track.albumArtist, track.album) === key ||
        albumKey(artist, track.album) === key)
    )
  }
  return artistKey(artist) === artistKey(item.name)
}

/**
 * `tracks` after `action` ('hide' or 'show') on `items`, so the lists
 * on screen follow without waiting for a reload. A track keeps the
 * widest rule that hides it; showing clears only a rule of the shown
 * kind.
 */
export function applyVisibility(tracks, action, items) {
  return tracks.map((track) => {
    let hiddenBy = track.hiddenBy
    for (const item of items) {
      if (!matches(track, item)) continue
      if (action === 'hide') {
        if (RANK[item.kind] > RANK[hiddenBy]) hiddenBy = item.kind
      } else if (hiddenBy === item.kind) {
        hiddenBy = ''
      }
    }
    return hiddenBy === track.hiddenBy ? track : { ...track, hiddenBy }
  })
}

/**
 * `GET /api/library/visibility` as the settings list shows it: one group
 * per kind, each row with the API item that shows it again.
 */
export function hiddenGroups(data) {
  const payload = data || {}
  return [
    {
      id: 'artists',
      icon: 'user',
      rows: (payload.artists || []).map((row) => ({
        key: `artist:${row.key}`,
        title: row.name || row.label,
        subtitle: '',
        item: { kind: 'artist', name: row.name || row.label },
      })),
    },
    {
      id: 'albums',
      icon: 'disc',
      rows: (payload.albums || []).map((row) => ({
        key: `album:${row.key}`,
        title: row.title || row.label,
        subtitle: row.artist || '',
        item: { kind: 'album', artist: row.artist || '', title: row.title },
      })),
    },
    {
      id: 'tracks',
      icon: 'music',
      rows: (payload.tracks || []).map((row) => ({
        key: `track:${row.key}`,
        title: row.label || row.file,
        subtitle: row.detail || '',
        item: { kind: 'track', file: row.file, key: row.key },
      })),
    },
  ]
}
