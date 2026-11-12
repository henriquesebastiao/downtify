import { describe, expect, it } from 'vitest'
import {
  STAT_SORT_KEYS,
  formatRate,
  libraryRouteFor,
  matchesTrackFilter,
  providerBreakdown,
  providerLabelKey,
  sparkline,
  statValue,
  statsById,
  trackFilterCounts,
  trendDisplay,
  watchRouteFor,
} from '../lib/watchStats'
import { WATCH_SORT_KEYS, sortWatches } from '../lib/watches'

const NOW = Date.parse('2026-10-27T12:00:00Z')

function stats(id, { added = 0, perDay = 0, bytes = 0, unique = 0, mine = 0 }) {
  return {
    id,
    period: { added, bytes },
    rate: { per_day: perDay },
    storage: { unique_bytes: unique },
    status: { downloaded: mine },
  }
}

function song(file, outcome, daysAgo) {
  return {
    file,
    watch: {
      outcome,
      added_at: new Date(NOW - daysAgo * 86400000).toISOString(),
    },
  }
}

describe('watch statistics', () => {
  it('reads the number each statistics sort orders by', () => {
    const row = stats(1, {
      added: 12,
      perDay: 1.5,
      bytes: 900,
      unique: 400,
      mine: 30,
    })
    expect(statValue(row, 'activity')).toBe(12)
    expect(statValue(row, 'rate')).toBe(1.5)
    expect(statValue(row, 'growth')).toBe(900)
    expect(statValue(row, 'storage')).toBe(400)
    expect(statValue(row, 'contributed')).toBe(30)
    expect(statValue(undefined, 'activity')).toBe(0)
    expect(statValue(row, 'name')).toBe(0)
  })

  it('sorts watches by their statistics, unknown ones as zero', () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }]
    const byId = statsById({
      watches: [stats(1, { added: 3 }), stats(2, { added: 15 })],
    })
    expect(STAT_SORT_KEYS.every((key) => WATCH_SORT_KEYS.includes(key))).toBe(
      true
    )
    expect(
      sortWatches(items, 'activity', 'desc', byId).map((i) => i.id)
    ).toEqual([2, 1, 3])
    expect(sortWatches(items, 'activity', 'asc', byId)[0].id).toBe(3)
    // No statistics loaded yet: the order is kept.
    expect(sortWatches(items, 'rate', 'desc').map((i) => i.id)).toEqual([
      1, 2, 3,
    ])
  })

  it('draws trends and sparklines', () => {
    expect(trendDisplay('up')).toMatchObject({ icon: 'trending', flip: false })
    expect(trendDisplay('down')).toMatchObject({ icon: 'trending', flip: true })
    expect(trendDisplay('nonsense').label).toBe('watchStats.trendNew')
    expect(sparkline([0, 5, 10])).toEqual([0, 0.5, 1])
    expect(sparkline([0, 0])).toEqual([0, 0])
    expect(sparkline(null)).toEqual([])
  })

  it('formats rates and providers', () => {
    expect(formatRate(2.14)).toBe('2.1')
    expect(formatRate(15.6)).toBe('16')
    expect(formatRate(0)).toBe('0')
    expect(providerLabelKey('slskd')).toBe('settings.sourceSlskd')
    expect(providerLabelKey('unknown')).toBe('playlistSearch.unknownSource')
    expect(providerLabelKey('something-new')).toBe(null)
    expect(
      providerBreakdown({ slskd: 1, 'youtube-music': 3, none: 0 })
    ).toEqual([
      { id: 'youtube-music', count: 3, share: 0.75 },
      { id: 'slskd', count: 1, share: 0.25 },
    ])
  })

  it("filters a watch's songs by how and when they got there", () => {
    const tracks = [
      song('a', 'downloaded', 1),
      song('b', 'linked', 2),
      song('c', 'downloaded', 40),
      song('d', 'unknown', 100),
      { file: 'e' },
    ]
    expect(trackFilterCounts(tracks, 30, NOW)).toEqual({
      all: 5,
      recent: 2,
      downloaded: 2,
      linked: 1,
      unknown: 2,
    })
    expect(matchesTrackFilter(tracks[2], 'recent', 90, NOW)).toBe(true)
  })

  it('links a watch to its Library page and its own page', () => {
    expect(libraryRouteFor({ name: 'Mix', kind: 'playlist' })).toEqual({
      name: 'Playlist',
      query: { name: 'Mix' },
    })
    expect(libraryRouteFor({ name: 'Björk', kind: 'artist' })).toEqual({
      name: 'Artist',
      query: { name: 'Björk' },
    })
    expect(libraryRouteFor(null)).toBe(null)
    expect(watchRouteFor({ id: 7 })).toEqual({
      name: 'MonitorWatch',
      params: { id: 7 },
    })
  })
})
