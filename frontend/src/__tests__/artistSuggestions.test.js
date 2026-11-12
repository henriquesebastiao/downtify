import { describe, expect, it } from 'vitest'
import {
  appendSuggestionPage,
  emptySuggestionPage,
} from '../lib/artistSuggestions'

const page = (names, next_offset = null, total = names.length) => ({
  items: names.map((name) => ({ name })),
  total,
  next_offset,
})

describe('appendSuggestionPage', () => {
  it('adds the next page below the first', () => {
    const merged = appendSuggestionPage(
      page(['A', 'B'], 2, 3),
      page(['C'], null, 3)
    )
    expect(merged.items.map((row) => row.name)).toEqual(['A', 'B', 'C'])
    expect(merged.next_offset).toBeNull()
    expect(merged.total).toBe(3)
  })

  it('does not repeat an artist the list shifted onto the next page', () => {
    const merged = appendSuggestionPage(
      page(['A', 'B'], 2),
      page(['B', 'C'], 4, 6)
    )
    expect(merged.items.map((row) => row.name)).toEqual(['A', 'B', 'C'])
    expect(merged.next_offset).toBe(4)
  })

  it('starts from an empty list', () => {
    expect(emptySuggestionPage()).toEqual({
      items: [],
      total: 0,
      next_offset: null,
    })
    expect(
      appendSuggestionPage(emptySuggestionPage(), page(['A'])).items
    ).toEqual([{ name: 'A' }])
  })
})
