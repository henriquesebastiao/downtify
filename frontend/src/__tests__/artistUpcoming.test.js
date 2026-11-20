import { describe, expect, it } from 'vitest'
import {
  comingDate,
  filterCounts,
  isOn,
  stateLabel,
} from '/src/lib/artistReleases'

const today = new Date(2026, 10, 19)

describe('comingDate', () => {
  it('is as short as the date allows', () => {
    expect(comingDate('2026-12-05', 'en-GB', today)).toBe('5 Dec')
    expect(comingDate('2027-01-08', 'en-GB', today)).toBe('8 Jan 2027')
    expect(comingDate('2026-12', 'en-GB', today)).toBe('Dec 2026')
    expect(comingDate('2027', 'en-GB', today)).toBe('2027')
    expect(comingDate('', 'en-GB', today)).toBe('')
  })
})

describe('upcoming releases', () => {
  const release = { state: 'upcoming', release_date: '2026-12-05' }

  it('reads "Coming <date>"', () => {
    const t = (key, values) => `${key}:${JSON.stringify(values || {})}`
    expect(stateLabel(release, t, 'en-GB')).toContain(
      'artistReleases.state.upcoming:'
    )
    expect(stateLabel({ state: 'upcoming' }, t)).toBe(
      'artistReleases.state.upcomingNoDate:{}'
    )
  })

  it('counts under its own chip and is switched on', () => {
    expect(filterCounts([release]).upcoming).toBe(1)
    expect(isOn({ state: 'upcoming' })).toBe(true)
  })
})
