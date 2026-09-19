import { describe, expect, it } from 'vitest'
import {
  dropProvider,
  moveProvider,
  providerRows,
  toggleProvider,
} from '../lib/providerOrder.js'

const ALL = ['slskd', 'youtube-music', 'youtube']

describe('providerRows', () => {
  it('numbers the enabled ones and parks the rest', () => {
    expect(providerRows(ALL, ['youtube-music', 'slskd'])).toEqual([
      { id: 'youtube-music', enabled: true, position: 1 },
      { id: 'slskd', enabled: true, position: 2 },
      { id: 'youtube', enabled: false, position: 0 },
    ])
  })

  it('merges in the labels and ignores unknown ids', () => {
    const rows = providerRows(['a'], ['a', 'gone'], { a: { title: 'A' } })
    expect(rows).toEqual([{ id: 'a', enabled: true, position: 1, title: 'A' }])
  })
})

describe('toggleProvider', () => {
  it('appends when switched on', () => {
    expect(toggleProvider(['youtube'], 'youtube-music', true)).toEqual([
      'youtube',
      'youtube-music',
    ])
  })

  it('can put one first instead', () => {
    expect(toggleProvider(['youtube'], 'slskd', true, { first: true })).toEqual(
      ['slskd', 'youtube']
    )
  })

  it('removes when switched off', () => {
    expect(toggleProvider(ALL, 'youtube-music', false)).toEqual([
      'slskd',
      'youtube',
    ])
  })

  it('refuses to leave the list empty unless allowed', () => {
    expect(toggleProvider(['youtube'], 'youtube', false)).toBeNull()
    expect(
      toggleProvider(['youtube'], 'youtube', false, { allowEmpty: true })
    ).toEqual([])
  })

  it('ignores switching on something already on', () => {
    expect(toggleProvider(['youtube'], 'youtube', true)).toBeNull()
  })
})

describe('moveProvider', () => {
  it('swaps with the neighbour', () => {
    expect(moveProvider(ALL, 'youtube-music', -1)).toEqual([
      'youtube-music',
      'slskd',
      'youtube',
    ])
    expect(moveProvider(ALL, 'youtube-music', 1)).toEqual([
      'slskd',
      'youtube',
      'youtube-music',
    ])
  })

  it('stops at the ends and ignores unknown ids', () => {
    expect(moveProvider(ALL, 'slskd', -1)).toBeNull()
    expect(moveProvider(ALL, 'youtube', 1)).toBeNull()
    expect(moveProvider(ALL, 'nope', 1)).toBeNull()
  })
})

describe('dropProvider', () => {
  it('moves a provider to another one’s slot', () => {
    expect(dropProvider(ALL, 'youtube', 'slskd')).toEqual([
      'youtube',
      'slskd',
      'youtube-music',
    ])
    expect(dropProvider(ALL, 'slskd', 'youtube')).toEqual([
      'youtube-music',
      'youtube',
      'slskd',
    ])
  })

  it('ignores a drop on itself or on a disabled provider', () => {
    expect(dropProvider(ALL, 'slskd', 'slskd')).toBeNull()
    expect(dropProvider(['slskd'], 'slskd', 'youtube')).toBeNull()
  })
})
