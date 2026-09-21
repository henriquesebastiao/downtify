import { describe, expect, it } from 'vitest'

import {
  PANEL_IDS,
  availablePanels,
  defaultPanel,
  requestedPanel,
} from '../lib/panels.js'

describe('availablePanels', () => {
  it('offers every panel while lyrics are shown', () => {
    expect(availablePanels({ lyrics: true })).toEqual(PANEL_IDS)
    // Lyrics are the default, so leaving the option out changes nothing.
    expect(availablePanels()).toEqual(PANEL_IDS)
  })

  it('drops only the lyrics panel when they are hidden', () => {
    expect(availablePanels({ lyrics: false })).toEqual([
      'queue',
      'details',
      'equalizer',
    ])
  })

  it('drops the lyrics panel for a podcast episode even when lyrics are on', () => {
    expect(availablePanels({ lyrics: true, isPodcast: true })).toEqual([
      'queue',
      'details',
      'equalizer',
    ])
  })
})

describe('requestedPanel', () => {
  const on = availablePanels({ lyrics: true })
  const off = availablePanels({ lyrics: false })

  it('honours a panel that is on offer', () => {
    expect(requestedPanel('queue', on)).toBe('queue')
    expect(requestedPanel('lyrics', on)).toBe('lyrics')
  })

  it('ignores a link to lyrics once they are hidden', () => {
    // An old ?panel=lyrics link or bookmark must not land on an empty tab.
    expect(requestedPanel('lyrics', off)).toBe('')
    expect(requestedPanel('queue', off)).toBe('queue')
  })

  it('ignores anything that is not a panel', () => {
    expect(requestedPanel('nonsense', on)).toBe('')
    expect(requestedPanel(undefined, on)).toBe('')
    expect(requestedPanel(null, on)).toBe('')
    expect(requestedPanel('', on)).toBe('')
  })
})

describe('defaultPanel', () => {
  it('opens on the lyrics while they are shown', () => {
    expect(defaultPanel({ lyrics: true })).toBe('lyrics')
    expect(defaultPanel()).toBe('lyrics')
  })

  it('falls back to a panel that exists when they are hidden', () => {
    const fallback = defaultPanel({ lyrics: false })
    expect(fallback).toBe('queue')
    // Never a panel the view doesn't offer.
    expect(availablePanels({ lyrics: false })).toContain(fallback)
  })

  it('falls back to the queue for a podcast episode even with lyrics on', () => {
    expect(defaultPanel({ lyrics: true, isPodcast: true })).toBe('queue')
  })
})
