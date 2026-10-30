import { describe, expect, it, vi } from 'vitest'

import { centerWithin } from '../lib/lyricsScroll.js'

const fakeContainer = (clientHeight = 600) => ({
  clientHeight,
  scrollTo: vi.fn(),
})

const fakeLine = (offsetTop, offsetHeight = 40) => ({
  offsetTop,
  offsetHeight,
  scrollIntoView: vi.fn(),
})

describe('centerWithin', () => {
  it('puts the middle of a line in the middle of the container', () => {
    const container = fakeContainer()
    centerWithin(container, fakeLine(1000))
    // The line's middle (1020) less half the container (300).
    expect(container.scrollTo).toHaveBeenCalledWith({
      top: 720,
      behavior: 'smooth',
    })
  })

  it('asks for the top for a line that cannot reach the middle', () => {
    // The browser clamps it, here and past the end of the lyrics.
    const container = fakeContainer()
    centerWithin(container, fakeLine(100))
    expect(container.scrollTo).toHaveBeenCalledWith({
      top: -180,
      behavior: 'smooth',
    })
  })

  it('never asks the line to scroll its ancestors', () => {
    const line = fakeLine(1000)
    centerWithin(fakeContainer(), line)
    expect(line.scrollIntoView).not.toHaveBeenCalled()
  })

  it('does nothing while the container or the line is missing', () => {
    const container = fakeContainer()
    centerWithin(container, null)
    expect(container.scrollTo).not.toHaveBeenCalled()
    expect(() => centerWithin(null, fakeLine(1000))).not.toThrow()
  })
})
