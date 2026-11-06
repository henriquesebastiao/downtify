import { describe, expect, it } from 'vitest'
import { djPresentation } from '../model/djPresentation'
const session = {
  tracks: [{ id: 'a' }, { id: 'b' }],
  timeline: [
    { id: 'a', start: 0, end: 100 },
    { id: 'b', start: 90, end: 190 },
    { id: 'a', start: 180, end: 280 },
  ],
}
describe('audible DJ decks', () => {
  it('shows current and next without animating before overlap', () => {
    const result = djPresentation(session, 85)
    expect(result.current.id).toBe('a')
    expect(result.next.id).toBe('b')
    expect(result.transition).toBeNull()
  })
  it('animates only the actual audio overlap', () => {
    expect(djPresentation(session, 90).transition).toBe(0)
    expect(djPresentation(session, 95).transition).toBe(0.5)
    expect(djPresentation(session, 100).current.id).toBe('b')
    expect(djPresentation(session, 100).transition).toBeNull()
  })
  it('handles repeated occurrences and absolute positions', () => {
    const result = djPresentation(session, 200)
    expect(result.current.id).toBe('a')
    expect(result.next).toBeUndefined()
    expect(result.elapsed).toBe(20)
    expect(result.duration).toBe(100)
  })
  it('accepts an empty or pruned timeline', () => {
    expect(djPresentation({}, 0).current).toBeUndefined()
    expect(
      djPresentation({ ...session, timeline: session.timeline.slice(1) }, 95)
        .current.id
    ).toBe('b')
  })
})
