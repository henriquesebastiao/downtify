import { describe, expect, it } from 'vitest'
import { buildPlaylists, sortItems, splitPlaylists } from '../lib/library'

describe('playlist favorites', () => {
  const rows = [
    { name: 'Ordinary', favorite: false, mine: true },
    { name: 'Pinned', favorite: true, mine: true },
  ]
  it('retains the account preference and pins it before other playlists', () => {
    const built = buildPlaylists(rows, new Map())
    expect(built.map((p) => p.name)).toEqual(['Pinned', 'Ordinary'])
    expect(built[0].favorite).toBe(true)
  })
  it('keeps favorites first even when the user reverses a title sort', () => {
    expect(sortItems(rows, 'title', 'desc')[0].name).toBe('Pinned')
    expect(sortItems(rows, 'title', 'asc')[0].name).toBe('Pinned')
  })
  it('preserves priority within shared and public lists without changing access', () => {
    const lists = splitPlaylists([
      { name: 'A', mine: false, sharedWithMe: true },
      { name: 'Z', mine: false, sharedWithMe: true, favorite: true },
      { name: 'Public', mine: false, favorite: true },
    ])
    expect(lists.own).toEqual([])
    expect(lists.shared.map((p) => p.name)).toEqual(['Z', 'A'])
    expect(lists.public[0].name).toBe('Public')
  })
})
