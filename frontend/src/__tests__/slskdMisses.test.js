import { describe, expect, it } from 'vitest'
import { fallbackRows, missRows, reasonOf } from '/src/lib/slskdMisses'

describe('slskd misses', () => {
  it('lists reasons most frequent first, unknown ones folded together', () => {
    const rows = missRows({
      reasons: [
        { reason: 'no_results', count: 2 },
        { reason: 'quality_filtered', count: 6 },
        { reason: 'something_new', count: 1 },
        { reason: 'unknown', count: 1 },
      ],
    })
    expect(rows.map((r) => [r.reason, r.count, r.share])).toEqual([
      ['quality_filtered', 6, 1],
      ['no_results', 2, 2 / 6],
      ['unknown', 2, 2 / 6],
    ])
    expect(reasonOf({ reason: 'tag_mismatch' })).toBe('tag_mismatch')
    expect(missRows(null)).toEqual([])
  })

  it('lists what was used instead', () => {
    expect(
      fallbackRows({ fallbacks: { youtube: 1, 'youtube-music': 4 } })
    ).toEqual([
      { source: 'youtube-music', count: 4 },
      { source: 'youtube', count: 1 },
    ])
  })
})
