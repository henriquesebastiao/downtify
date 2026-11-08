import { describe, expect, it } from 'vitest'

import {
  ROW_GAP,
  columnGap,
  columnsFor,
  estimateRowHeight,
  rowItems,
} from '../lib/virtualGrid.js'

describe('columnsFor', () => {
  it('follows the grid-cols breakpoints', () => {
    expect(columnsFor(360)).toBe(2)
    expect(columnsFor(639)).toBe(2)
    expect(columnsFor(640)).toBe(3)
    expect(columnsFor(768)).toBe(4)
    expect(columnsFor(1024)).toBe(5)
    expect(columnsFor(1536)).toBe(6)
    expect(columnsFor(1900)).toBe(7)
    expect(columnsFor(3840)).toBe(7)
  })
})

describe('estimateRowHeight', () => {
  it('is a square cover plus its text and the row gap', () => {
    // 5 columns, 20px gaps: (1000 - 80) / 5 = 184px tiles.
    expect(estimateRowHeight(1000, 5, 1200)).toBe(184 + 52 + ROW_GAP)
    expect(columnGap(390)).toBe(16)
  })

  it('never goes negative before the container is measured', () => {
    expect(estimateRowHeight(0, 5, 1200)).toBe(52 + ROW_GAP)
  })
})

describe('rowItems', () => {
  it('slices a row of columns, the last one possibly short', () => {
    const items = ['a', 'b', 'c', 'd', 'e']
    expect(rowItems(items, 0, 2)).toEqual(['a', 'b'])
    expect(rowItems(items, 2, 2)).toEqual(['e'])
    expect(rowItems(items, 3, 2)).toEqual([])
  })
})
