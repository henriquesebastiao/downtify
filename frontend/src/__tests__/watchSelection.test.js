import { describe, expect, it } from 'vitest'
import {
  keepExisting,
  shownState,
  toggleShown,
  toggleWatch,
} from '../lib/watchSelection.js'
import {
  intervalLabel,
  intervalOptions,
} from '../components/monitor/intervals.js'

const shown = [1, 2, 3, 4, 5]

describe('toggleWatch', () => {
  it('picks and unpicks one watch', () => {
    const one = toggleWatch(new Set(), shown, 3)
    expect([...one]).toEqual([3])
    expect([...toggleWatch(one, shown, 3)]).toEqual([])
  })

  it('picks everything between the last click and a shift-click', () => {
    const next = toggleWatch(new Set([2]), shown, 4, {
      anchor: 2,
      range: true,
    })
    expect([...next].sort()).toEqual([2, 3, 4])
  })

  it('works upwards too', () => {
    const next = toggleWatch(new Set(), shown, 1, { anchor: 3, range: true })
    expect([...next].sort()).toEqual([1, 2, 3])
  })

  it('a shift-click on a picked watch unpicks the range', () => {
    const next = toggleWatch(new Set([1, 2, 3, 4, 5]), shown, 4, {
      anchor: 2,
      range: true,
    })
    expect([...next].sort()).toEqual([1, 5])
  })

  it('without an anchor still shown, a shift-click is a plain click', () => {
    const next = toggleWatch(new Set(), shown, 4, { anchor: 99, range: true })
    expect([...next]).toEqual([4])
  })

  it('does not change the Set it was given', () => {
    const before = new Set([1])
    toggleWatch(before, shown, 2)
    expect([...before]).toEqual([1])
  })
})

describe('the box above the list', () => {
  it('tells none, some or all of the shown watches', () => {
    expect(shownState(new Set(), shown)).toBe('none')
    expect(shownState(new Set([1, 9]), shown)).toBe('some')
    expect(shownState(new Set(shown), shown)).toBe('all')
    expect(shownState(new Set([1]), [])).toBe('none')
  })

  it('picks every shown watch, keeping hidden picks', () => {
    const next = toggleShown(new Set([9]), shown)
    expect([...next].sort()).toEqual([1, 2, 3, 4, 5, 9])
  })

  it('unpicks only the shown watches when they all are picked', () => {
    const next = toggleShown(new Set([...shown, 9]), shown)
    expect([...next]).toEqual([9])
  })
})

describe('keepExisting', () => {
  it('drops watches no longer listed', () => {
    expect([...keepExisting(new Set([1, 2, 7]), [1, 2, 3])]).toEqual([1, 2])
  })

  it('returns the same Set when nothing changed', () => {
    const selected = new Set([1, 2])
    expect(keepExisting(selected, [1, 2, 3])).toBe(selected)
  })
})

describe('check intervals', () => {
  const t = (key, { count }) => `${key}:${count}`

  it('offers every 3 days between every day and every week', () => {
    const values = intervalOptions(t).map((option) => option.value)
    expect(
      values.slice(values.indexOf(1440), values.indexOf(10080) + 1)
    ).toEqual([1440, 4320, 10080])
    expect(intervalLabel(t, 4320)).toBe('monitor.everyDays:3')
  })
})
