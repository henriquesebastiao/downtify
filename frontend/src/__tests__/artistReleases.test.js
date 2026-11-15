import { describe, expect, it } from 'vitest'
import {
  canSwitch,
  filterCounts,
  isOn,
  matchesFilter,
  sectioned,
  sourceNames,
  stateTone,
} from '../lib/artistReleases.js'

const release = (name, state, extra = {}) => ({
  id: name,
  name,
  state,
  section: 'album',
  year: '2016',
  sources: ['deezer'],
  ...extra,
})

describe('artist releases', () => {
  const releases = [
    release('Views', 'complete'),
    release('Take Care', 'partly', { year: '2011' }),
    release('Scary Hours', 'missing', { section: 'ep', year: '2018' }),
    release('Room for Improvement', 'skipped', {
      section: 'mixtape',
      year: '2006',
    }),
    release('Work', 'not_own', { section: 'single' }),
    release('Live at the O2', 'off', { section: 'other' }),
  ]

  it('switches on what the watch downloads', () => {
    expect(isOn(releases[0])).toBe(true)
    expect(isOn(releases[2])).toBe(true)
    expect(isOn(releases[3])).toBe(false)
    expect(isOn(releases[5])).toBe(false)
    expect(canSwitch(releases[4])).toBe(false)
    expect(canSwitch(releases[3])).toBe(true)
  })

  it('filters, leaving guest spots to their own chip', () => {
    expect(matchesFilter(releases[4], 'all')).toBe(false)
    expect(matchesFilter(releases[4], 'not_own')).toBe(true)
    // Out before a "new releases only" watch counts as not watched.
    expect(matchesFilter(releases[3], 'not_watched')).toBe(true)
    const counts = filterCounts(releases)
    expect(counts.all).toBe(5)
    expect(counts.complete).toBe(1)
    expect(counts.off).toBe(1)
  })

  it('lists sections in order, newest first', () => {
    const sections = sectioned(releases)
    expect(sections.map((s) => s.id)).toEqual([
      'album',
      'mixtape',
      'ep',
      'other',
    ])
    expect(sections[0].releases.map((r) => r.name)).toEqual([
      'Views',
      'Take Care',
    ])
    expect(sectioned(releases, 'missing').map((s) => s.id)).toEqual(['ep'])
  })

  it('names catalogues and tones states', () => {
    expect(sourceNames({ sources: ['youtube', 'deezer', 'musicbrainz'] })).toBe(
      'YouTube Music, Deezer, MusicBrainz'
    )
    expect(stateTone('complete')).toBe('accent')
    expect(stateTone('partly')).toBe('warn')
    expect(stateTone('nope')).toBe('neutral')
  })
})
