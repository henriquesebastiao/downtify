import { describe, expect, it } from 'vitest'
import { mobilePaginationItems, paginationItems } from '../model/pagination.js'

describe('paginationItems', () => {
  it('returns every page when the total fits without condensing', () => {
    expect(paginationItems(1, 5)).toEqual([1, 2, 3, 4, 5])
    expect(paginationItems(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it('matches the exact example from the feature request', () => {
    // "1 2 3 ... 36 37 38" — current page near the start of a long list.
    expect(paginationItems(1, 38)).toEqual([1, 2, 3, 'ellipsis', 36, 37, 38])
  })

  it('condenses with two ellipses when current is far from both ends', () => {
    expect(paginationItems(20, 38)).toEqual([
      1,
      2,
      3,
      'ellipsis',
      19,
      20,
      21,
      'ellipsis',
      36,
      37,
      38,
    ])
  })

  it('condenses with one ellipsis when current is near the end', () => {
    expect(paginationItems(38, 38)).toEqual([1, 2, 3, 'ellipsis', 36, 37, 38])
  })

  it('merges the sibling window into the start boundary with no ellipsis', () => {
    // current=4 with boundaryCount=3, siblingCount=1 -> siblings [3,4,5]
    // overlap the [1,2,3] boundary, so it's one contiguous run.
    expect(paginationItems(4, 38)).toEqual([
      1,
      2,
      3,
      4,
      5,
      'ellipsis',
      36,
      37,
      38,
    ])
  })

  it('never duplicates a page that is in both a boundary and the sibling window', () => {
    const items = paginationItems(2, 38)
    const numbers = items.filter((i) => i !== 'ellipsis')
    expect(new Set(numbers).size).toBe(numbers.length)
  })

  it('handles a single page', () => {
    expect(paginationItems(1, 1)).toEqual([1])
  })

  it('handles zero pages', () => {
    expect(paginationItems(1, 0)).toEqual([])
  })

  it('respects custom boundaryCount/siblingCount', () => {
    expect(
      paginationItems(20, 38, { boundaryCount: 1, siblingCount: 0 })
    ).toEqual([1, 'ellipsis', 20, 'ellipsis', 38])
  })
})

describe('mobilePaginationItems', () => {
  it('reuses the full desktop list for a small total (fits fine either way)', () => {
    expect(mobilePaginationItems(3, 5)).toEqual(paginationItems(3, 5))
    expect(mobilePaginationItems(3, 5)).toEqual([1, 2, 3, 4, 5])
  })

  it('never returns more items than the inline threshold allows', () => {
    for (let total = 1; total <= 50; total++) {
      for (let current = 1; current <= total; current++) {
        const items = mobilePaginationItems(current, total)
        expect(items.length).toBeLessThanOrEqual(8)
      }
    }
  })

  it('the tight fallback window itself never exceeds 5 items', () => {
    // Forced past the inline threshold regardless of how short the
    // list actually is, to isolate the fallback branch's own output size.
    for (let total = 1; total <= 50; total++) {
      for (let current = 1; current <= total; current++) {
        expect(
          mobilePaginationItems(current, total, -1).length
        ).toBeLessThanOrEqual(5)
      }
    }
  })

  it('falls back to a tight first/current/last window for a long list', () => {
    // The exact scenario reported: page 36 of 41 wrapped onto a second
    // row on mobile with the plain (desktop) condensed list.
    expect(mobilePaginationItems(36, 41)).toEqual([
      1,
      'ellipsis',
      36,
      'ellipsis',
      41,
    ])
  })

  it('always keeps the current page reachable in the fallback window', () => {
    for (let total = 9; total <= 60; total += 7) {
      for (let current = 1; current <= total; current += 3) {
        expect(mobilePaginationItems(current, total)).toContain(current)
      }
    }
  })

  it('respects a custom inline threshold', () => {
    // paginationItems(1, 7) is the full [1..7] range (7 items); with a
    // threshold of 6 that's too long to show inline anymore.
    expect(paginationItems(1, 7).length).toBe(7)
    expect(mobilePaginationItems(1, 7, 6)).toEqual([1, 'ellipsis', 7])
  })
})
