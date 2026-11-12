import { describe, expect, it } from 'vitest'
import {
  breakdownRows,
  cleanupSummary,
  daysLeftTone,
  folderKinds,
  formatDay,
  growthChart,
  linePath,
  measuredFrom,
  nearestIndex,
  outcomeBars,
  providerRows,
} from '../lib/libraryUsage'

function point(day, bytes, estimated = false) {
  return { day, bytes, files: 1, estimated }
}

describe('library usage', () => {
  it('draws a path through points', () => {
    expect(linePath([])).toBe('')
    expect(
      linePath([
        { x: 0, y: 10 },
        { x: 5.123, y: 2 },
      ])
    ).toBe('M0 10 L5.12 2')
  })

  it('splits the growth line into its estimated and measured days', () => {
    const chart = growthChart(
      [
        point('2026-10-25', 100, true),
        point('2026-10-26', 200, true),
        point('2026-10-27', 300),
      ],
      { width: 100, height: 50 }
    )

    expect(chart.coords.map((c) => c.x)).toEqual([0, 50, 100])
    // The highest size sits under the top, the lowest over the bottom.
    expect(chart.coords[2].y).toBeGreaterThan(0)
    expect(chart.coords[0].y).toBeLessThan(50)
    expect(chart.max).toBeGreaterThan(300)
    expect(chart.min).toBeLessThan(100)
    // The dashed half runs into the first measured day.
    expect(chart.estimated.split(' L')).toHaveLength(3)
    expect(chart.measured.split(' L')).toHaveLength(1)
    expect(chart.area.endsWith('Z')).toBe(true)
  })

  it('keeps a flat line off the edges and never below zero', () => {
    const flat = growthChart([point('a', 0), point('b', 0)], {
      width: 10,
      height: 10,
    })
    expect(flat.min).toBe(0)
    expect(flat.max).toBeGreaterThan(0)
    expect(flat.estimated).toBe('')

    const steady = growthChart([point('a', 500), point('b', 500)], {
      height: 10,
    })
    expect(steady.coords[0].y).toBe(5)
  })

  it('has nothing to draw without points', () => {
    expect(growthChart([])).toMatchObject({ coords: [], area: '' })
  })

  it('finds the point nearest to the pointer', () => {
    expect(nearestIndex(0, 10)).toBe(0)
    expect(nearestIndex(0.5, 11)).toBe(5)
    expect(nearestIndex(1.4, 10)).toBe(9)
    expect(nearestIndex(-1, 10)).toBe(0)
    expect(nearestIndex(0.7, 1)).toBe(0)
  })

  it('sizes breakdown bars against the biggest row', () => {
    expect(
      breakdownRows([
        { id: 'slskd', files: 2, bytes: 400 },
        { id: 'youtube', files: 4, bytes: 100 },
        { id: 'empty', files: 0, bytes: 0 },
      ])
    ).toEqual([
      { id: 'slskd', files: 2, bytes: 400, share: 1 },
      { id: 'youtube', files: 4, bytes: 100, share: 0.25 },
    ])
  })

  it('adds what each provider brought in during the period', () => {
    const rows = providerRows(
      { by_provider: [{ id: 'slskd', files: 3, bytes: 90 }] },
      { by_provider: [{ id: 'slskd', files: 1, bytes: 30 }] }
    )
    expect(rows[0]).toMatchObject({ added: 30, addedFiles: 1 })
    expect(providerRows(null, null)).toEqual([])
  })

  it('lists a folder by kind, biggest first', () => {
    expect(
      folderKinds({
        kinds: {
          lyrics: { files: 9, bytes: 10 },
          audio: { files: 1, bytes: 500 },
        },
      }).map((kind) => kind.id)
    ).toEqual(['audio', 'lyrics'])
  })

  it('adds up what could be cleaned, the scan once it is in', () => {
    const report = {
      duplicates: { files: 2, bytes: 20 },
      working: { files: 1, bytes: 5 },
    }

    const before = cleanupSummary(report, null)
    expect(before.leftovers).toBeNull()
    expect(before.total).toEqual({ files: 3, bytes: 25 })

    const after = cleanupSummary(report, {
      leftovers: { files: 1, bytes: 1 },
      orphans: { files: 4, bytes: 4 },
    })
    expect(after.total).toEqual({ files: 8, bytes: 30 })
  })

  it('puts every download outcome on one scale', () => {
    const bars = outcomeBars([
      { completed: 4, skipped: 2, failed: 0 },
      { completed: 1, skipped: 0, failed: 1 },
    ])
    expect(bars.completed.map((b) => b.height)).toEqual([1, 0.25])
    expect(bars.skipped[0]).toEqual({ count: 2, height: 0.5 })
    expect(bars.failed[1].height).toBe(0.25)
    expect(outcomeBars([]).failed).toEqual([])
  })

  it('warns as the disk gets close to full', () => {
    expect(daysLeftTone(10)).toBe('danger')
    expect(daysLeftTone(45)).toBe('warn')
    expect(daysLeftTone(400)).toBe('')
    expect(daysLeftTone(null)).toBe('')
  })

  it('tells from when the sizes are measured', () => {
    expect(
      measuredFrom([point('a', 1, true), point('b', 1), point('c', 1)])
    ).toBe('b')
    expect(measuredFrom([point('a', 1), point('b', 1)])).toBeNull()
    expect(measuredFrom([point('a', 1, true), point('b', 1)])).toBe('b')
    expect(measuredFrom([])).toBeNull()
  })

  it('writes a day the short way', () => {
    expect(formatDay('2026-10-27', 'en')).toBe('Oct 27')
    expect(formatDay('nope', 'en')).toBe('nope')
  })
})
