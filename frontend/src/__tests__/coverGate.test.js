import { describe, expect, it } from 'vitest'

import {
  COVER_DWELL_MS,
  cancelUnfinishedImages,
  coverDelay,
} from '../lib/coverGate.js'

describe('coverDelay', () => {
  it('asks at once on a page at rest, so opening a page is not delayed', () => {
    expect(coverDelay(1000, -Infinity)).toBe(0)
    expect(coverDelay(1000, 1000 - COVER_DWELL_MS)).toBe(0)
  })

  it('waits while the page is scrolling', () => {
    expect(coverDelay(1000, 999)).toBe(COVER_DWELL_MS)
    expect(coverDelay(1000, 1000 - COVER_DWELL_MS + 1)).toBe(COVER_DWELL_MS)
  })
})

function fakeImage(complete) {
  const attributes = new Set(['src', 'srcset'])
  return {
    complete,
    attributes,
    removeAttribute: (name) => attributes.delete(name),
  }
}

describe('cancelUnfinishedImages', () => {
  it('drops the request of an image still loading', () => {
    const image = fakeImage(false)
    cancelUnfinishedImages({ querySelectorAll: () => [image] })
    expect([...image.attributes]).toEqual([])
  })

  it('leaves a finished image alone', () => {
    const image = fakeImage(true)
    cancelUnfinishedImages({ querySelectorAll: () => [image] })
    expect([...image.attributes]).toEqual(['src', 'srcset'])
  })

  it('does nothing without an element', () => {
    expect(() => cancelUnfinishedImages(null)).not.toThrow()
  })
})
