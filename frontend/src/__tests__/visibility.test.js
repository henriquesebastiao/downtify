import { describe, expect, it } from 'vitest'

import { groupAlbums, groupArtists, normalizeTrack } from '../lib/library.js'
import {
  albumItem,
  applyVisibility,
  artistItem,
  hiddenGroups,
  selectionChanges,
  trackItem,
  visibilityAction,
} from '../lib/visibility.js'
import { ACTIVITY_KINDS, activityIcon } from '../lib/activity.js'

function row(file, extra = {}) {
  return {
    file,
    title: file.replace(/\.mp3$/, ''),
    artist: 'Ana',
    album_artist: 'Ana',
    album: 'Sun',
    ...extra,
  }
}

describe('hiddenBy on library rows', () => {
  it('reads hidden_by from /tracks', () => {
    expect(normalizeTrack(row('a.mp3')).hiddenBy).toBe('')
    expect(normalizeTrack(row('a.mp3', { hidden_by: 'album' })).hiddenBy).toBe(
      'album'
    )
  })

  it('marks an album only when a rule on it or its artist hides it', () => {
    const one = groupAlbums([
      normalizeTrack(row('a.mp3', { hidden_by: 'track' })),
      normalizeTrack(row('b.mp3')),
    ])
    expect(one[0].hiddenBy).toBe('')

    const viaAlbum = groupAlbums([
      normalizeTrack(row('a.mp3', { hidden_by: 'album' })),
      normalizeTrack(row('b.mp3', { hidden_by: 'album' })),
    ])
    expect(viaAlbum[0].hiddenBy).toBe('album')

    const viaArtist = groupAlbums([
      normalizeTrack(row('a.mp3', { hidden_by: 'album' })),
      normalizeTrack(row('b.mp3', { hidden_by: 'artist' })),
    ])
    expect(viaArtist[0].hiddenBy).toBe('artist')
  })

  it('marks an artist only when a rule on the artist hides them', () => {
    const tracks = [
      normalizeTrack(row('a.mp3', { hidden_by: 'album' })),
      normalizeTrack(row('b.mp3', { album: 'Moon', hidden_by: 'artist' })),
    ]
    expect(groupArtists(tracks)[0].hiddenBy).toBe('artist')
    expect(groupArtists([tracks[0]])[0].hiddenBy).toBe('')
  })
})

describe('what an admin may do', () => {
  it('hides what is shown and shows what its own rule hides', () => {
    expect(visibilityAction('', 'track')).toBe('hide')
    expect(visibilityAction('track', 'track')).toBe('show')
    // A wider rule has to be lifted where it was set.
    expect(visibilityAction('album', 'track')).toBeNull()
    expect(visibilityAction('artist', 'album')).toBeNull()
  })

  it('splits a selection into songs to hide and songs to show', () => {
    const tracks = [
      normalizeTrack(row('a.mp3')),
      normalizeTrack(row('b.mp3', { hidden_by: 'track' })),
      normalizeTrack(row('c.mp3', { hidden_by: 'album' })),
    ]
    expect(selectionChanges(tracks)).toEqual({
      hide: [{ kind: 'track', file: 'a.mp3' }],
      show: [{ kind: 'track', file: 'b.mp3' }],
    })
  })

  it('builds the API items', () => {
    expect(trackItem({ file: 'a.mp3' })).toEqual({
      kind: 'track',
      file: 'a.mp3',
    })
    expect(albumItem({ artist: 'Ana', title: 'Sun' })).toEqual({
      kind: 'album',
      artist: 'Ana',
      title: 'Sun',
    })
    expect(artistItem({ name: 'Ana' })).toEqual({ kind: 'artist', name: 'Ana' })
  })
})

describe('applyVisibility', () => {
  const tracks = [
    normalizeTrack(row('a.mp3')),
    normalizeTrack(row('b.mp3', { album: 'Moon' })),
    normalizeTrack(
      row('c.mp3', { artist: 'Bo', album_artist: 'Bo', album: 'Sea' })
    ),
  ]
  const hiddenBy = (list) => list.map((track) => track.hiddenBy)

  it('hides a track, an album or an artist, case-insensitively', () => {
    expect(
      hiddenBy(applyVisibility(tracks, 'hide', [trackItem(tracks[0])]))
    ).toEqual(['track', '', ''])
    expect(
      hiddenBy(
        applyVisibility(tracks, 'hide', [
          { kind: 'album', artist: 'ANA', title: 'sun' },
        ])
      )
    ).toEqual(['album', '', ''])
    expect(
      hiddenBy(
        applyVisibility(tracks, 'hide', [{ kind: 'artist', name: 'ana' }])
      )
    ).toEqual(['artist', 'artist', ''])
  })

  it('keeps the widest rule', () => {
    const once = applyVisibility(tracks, 'hide', [artistItem({ name: 'Ana' })])
    const twice = applyVisibility(once, 'hide', [trackItem(tracks[0])])
    expect(hiddenBy(twice)).toEqual(['artist', 'artist', ''])
  })

  it('shows only what the shown rule hid', () => {
    const hidden = applyVisibility(tracks, 'hide', [
      artistItem({ name: 'Ana' }),
    ])
    expect(
      hiddenBy(applyVisibility(hidden, 'show', [trackItem(tracks[0])]))
    ).toEqual(['artist', 'artist', ''])
    expect(
      hiddenBy(applyVisibility(hidden, 'show', [artistItem({ name: 'Ana' })]))
    ).toEqual(['', '', ''])
  })

  it('leaves untouched rows as they were', () => {
    const next = applyVisibility(tracks, 'hide', [trackItem(tracks[0])])
    expect(next[1]).toBe(tracks[1])
    expect(tracks[0].hiddenBy).toBe('')
  })
})

describe('hiddenGroups', () => {
  it('turns the API list into rows that show each item again', () => {
    const groups = hiddenGroups({
      artists: [{ key: 'ana', name: 'Ana', label: 'Ana' }],
      albums: [
        { key: 'ana\x1fsun', title: 'Sun', artist: 'Ana', label: 'Sun' },
      ],
      tracks: [
        {
          key: 'k1',
          file: 'Ana/One.mp3',
          label: 'Ana - One',
          detail: 'Sun',
        },
      ],
    })

    expect(groups.map((group) => group.id)).toEqual([
      'artists',
      'albums',
      'tracks',
    ])
    expect(groups[0].rows[0].item).toEqual({ kind: 'artist', name: 'Ana' })
    expect(groups[1].rows[0]).toMatchObject({
      title: 'Sun',
      subtitle: 'Ana',
      item: { kind: 'album', artist: 'Ana', title: 'Sun' },
    })
    expect(groups[2].rows[0]).toMatchObject({
      title: 'Ana - One',
      subtitle: 'Sun',
      item: { kind: 'track', file: 'Ana/One.mp3', key: 'k1' },
    })
  })

  it('copes with nothing', () => {
    expect(hiddenGroups(null).every((group) => !group.rows.length)).toBe(true)
  })
})

describe('activity', () => {
  it('knows the visibility kinds', () => {
    expect(ACTIVITY_KINDS).toContain('library_hidden')
    expect(ACTIVITY_KINDS).toContain('library_shown')
    expect(activityIcon('library_hidden')).toBe('eye-off')
    expect(activityIcon('library_shown')).toBe('eye')
  })
})
