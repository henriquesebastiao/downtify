import { describe, expect, it } from 'vitest'

import {
  ARTWORK_SIZES,
  CATEGORIES,
  artworkSizeFromDetail,
  byteProgress,
  canCancel,
  canPause,
  canResume,
  canScan,
  defaultSelection,
  foundCategories,
  groupJobs,
  isBusy,
  isWaitingToStart,
  normalizeStatus,
  queuedBytes,
  scanProgress,
  selectedTrackCount,
  toggleCategory,
  trackProgress,
} from '/src/lib/upgrade'

const counts = (over = {}) => normalizeStatus({ counts: over }).counts

describe('normalizeStatus', () => {
  it('fills in every field for an empty payload', () => {
    const status = normalizeStatus(null)
    expect(status.state).toBe('idle')
    expect(status.run).toBe(null)
    expect(status.counts.total).toBe(0)
    expect(status.summary.libraryTracks).toBe(0)
    expect(status.options).toEqual({})
  })

  it('maps the snake_case fields the backend sends', () => {
    const status = normalizeStatus({
      state: 'ready',
      run: { id: 3, options: { artwork_min_px: 900 } },
      counts: { total: 12, finished: 4 },
      scan: { scanned: 50, total: 100 },
      summary: {
        categories: { artwork: 12 },
        category_bytes: { artwork: 2048 },
        tracks: 12,
        recently_checked: 9,
        library_tracks: 40,
        library_bytes: 4096,
      },
    })

    expect(status.state).toBe('ready')
    expect(status.counts.total).toBe(12)
    expect(status.summary.categoryBytes.artwork).toBe(2048)
    expect(status.summary.recentlyChecked).toBe(9)
    expect(status.summary.libraryTracks).toBe(40)
    expect(status.options.artwork_min_px).toBe(900)
  })
})

describe('run state', () => {
  it('knows when work is happening', () => {
    expect(isBusy('scanning')).toBe(true)
    expect(isBusy('running')).toBe(true)
    expect(isBusy('paused')).toBe(false)
    expect(isBusy('idle')).toBe(false)
  })

  it('only offers a scan when nothing is running', () => {
    expect(canScan('idle')).toBe(true)
    expect(canScan('done')).toBe(true)
    expect(canScan('running')).toBe(false)
    expect(canScan('scanning')).toBe(false)
  })

  it('offers pause while running and resume while paused', () => {
    expect(canPause('running')).toBe(true)
    expect(canPause('paused')).toBe(false)
    expect(canResume('paused')).toBe(true)
    expect(canResume('running')).toBe(false)
  })

  it('can stop a run that started, but not a scan awaiting confirmation', () => {
    expect(canCancel('running')).toBe(true)
    expect(canCancel('paused')).toBe(true)
    expect(canCancel('ready')).toBe(false)
    expect(canCancel('done')).toBe(false)
  })

  it('waits for confirmation only when the scan found something', () => {
    expect(
      isWaitingToStart(
        normalizeStatus({ state: 'ready', counts: { total: 3 } })
      )
    ).toBe(true)
    expect(
      isWaitingToStart(
        normalizeStatus({ state: 'ready', counts: { total: 0 } })
      )
    ).toBe(false)
    expect(
      isWaitingToStart(
        normalizeStatus({ state: 'running', counts: { total: 3 } })
      )
    ).toBe(false)
  })
})

describe('progress', () => {
  it('counts every finished track, whatever the outcome', () => {
    expect(trackProgress(counts({ total: 8, finished: 2 }))).toEqual({
      done: 2,
      total: 8,
      pct: 25,
    })
  })

  it('is 0% rather than NaN on an empty queue', () => {
    expect(trackProgress(counts({})).pct).toBe(0)
    expect(byteProgress(counts({}), 0).pct).toBe(0)
    expect(scanProgress({ scanned: 0, total: 0 }).pct).toBe(0)
  })

  it('never reports more than 100%', () => {
    expect(trackProgress(counts({ total: 2, finished: 5 })).pct).toBe(100)
  })

  it('tracks bytes through the queue', () => {
    const progress = byteProgress(counts({ processed_bytes: 512 }), 2048)
    expect(progress).toEqual({ done: 512, total: 2048, pct: 25 })
  })

  it('reports scan progress', () => {
    expect(scanProgress({ scanned: 25, total: 200 }).pct).toBe(13)
  })
})

describe('what a scan found', () => {
  const summary = normalizeStatus({
    summary: {
      categories: { artwork: 16921, lyrics: 2104, metadata: 0 },
      category_bytes: { artwork: 90_000, lyrics: 12_000 },
    },
  }).summary

  it('lists only the categories with tracks behind', () => {
    expect(foundCategories(summary)).toEqual(['artwork', 'lyrics'])
  })

  it('pre-ticks everything it found', () => {
    expect(defaultSelection(summary)).toEqual(['artwork', 'lyrics'])
  })

  it('estimates the queue size from the biggest category', () => {
    // A track can need several repairs, so the categories overlap and
    // adding them up would overstate the work.
    expect(queuedBytes(summary)).toBe(90_000)
  })

  it('counts the tracks a selection would touch without double-counting', () => {
    expect(selectedTrackCount(summary, ['artwork', 'lyrics'])).toBe(16921)
    expect(selectedTrackCount(summary, ['lyrics'])).toBe(2104)
    expect(selectedTrackCount(summary, [])).toBe(0)
  })
})

describe('toggleCategory', () => {
  it('adds and removes, keeping the canonical order', () => {
    expect(toggleCategory(['lyrics'], 'artwork', true)).toEqual([
      'artwork',
      'lyrics',
    ])
    expect(toggleCategory(['artwork', 'lyrics'], 'artwork', false)).toEqual([
      'lyrics',
    ])
  })

  it('is idempotent', () => {
    expect(toggleCategory(['artwork'], 'artwork', true)).toEqual(['artwork'])
    expect(toggleCategory([], 'artwork', false)).toEqual([])
  })
})

describe('job rows', () => {
  it('groups by status, in the order the list shows them', () => {
    const groups = groupJobs([
      { file: 'a', status: 'done' },
      { file: 'b', status: 'running' },
      { file: 'c', status: 'failed' },
      { file: 'd', status: 'done' },
      { file: 'e', status: 'nonsense' },
    ])

    expect(groups.map((group) => group.status)).toEqual([
      'running',
      'failed',
      'done',
    ])
    expect(groups[2].jobs).toHaveLength(2)
  })

  it('has nothing to group when there are no jobs', () => {
    expect(groupJobs([])).toEqual([])
    expect(groupJobs(undefined)).toEqual([])
  })

  it('pulls the new cover size out of a detail line', () => {
    expect(artworkSizeFromDetail('artwork 1200px (itunes)')).toBe('1200px')
    expect(artworkSizeFromDetail('lyrics')).toBe('')
    expect(artworkSizeFromDetail(undefined)).toBe('')
  })
})

describe('offered choices', () => {
  it('matches the backend categories', () => {
    expect(CATEGORIES).toEqual(['artwork', 'lyrics', 'metadata'])
  })

  it('offers the sizes the issue asked for', () => {
    expect(ARTWORK_SIZES).toContain(300)
    expect(ARTWORK_SIZES).toContain(600)
    expect(ARTWORK_SIZES).toContain(1200)
  })
})
