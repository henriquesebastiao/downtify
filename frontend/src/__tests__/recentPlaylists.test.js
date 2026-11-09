import { describe, expect, it } from 'vitest'
import { playlistChoices, rememberPlaylist } from '../lib/recentPlaylists'

describe('compact playlist additions', () => {
  const playlists = Array.from({ length: 120 }, (_, i) => ({
    name: `p${i}`,
    title: `Playlist ${i}`,
  }))
  it('keeps three recent editable choices and every other choice exactly once', () => {
    const { quick, others } = playlistChoices(playlists, [
      'deleted',
      'p99',
      'p4',
      'p99',
      'p30',
    ])
    expect(quick.map((p) => p.name)).toEqual(['p99', 'p4', 'p30'])
    expect(others).toHaveLength(117)
    expect(new Set([...quick, ...others].map((p) => p.name)).size).toBe(120)
  })
  it('moves a successful addition to the top and bounds history', () => {
    expect(rememberPlaylist(['b', 'a', 'c'], 'a')).toEqual(['a', 'b', 'c'])
    expect(
      rememberPlaylist(
        playlists.map((p) => p.name),
        'new'
      )
    ).toHaveLength(100)
  })
})
