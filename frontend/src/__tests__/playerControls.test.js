import { describe, expect, it } from 'vitest'
import {
  CONTROL_PRIORITY,
  planControls,
} from '../components/shell/playerControls.js'

const ALL = [...CONTROL_PRIORITY]

describe('planControls (issue #552)', () => {
  it('shows everything before the bar has been measured', () => {
    const plan = planControls(0, ALL)
    expect([...plan.shown]).toEqual(ALL)
    expect(plan.overflow).toEqual([])
    expect(plan.volume).toBe('inline')
  })

  it('keeps everything on a bar with room for it', () => {
    const plan = planControls(1400, ALL)
    expect(plan.shown.size).toBe(ALL.length)
    expect(plan.overflow).toEqual([])
    expect(plan.volume).toBe('inline')
  })

  it('moves the least important controls out first', () => {
    const plan = planControls(800, ALL)
    expect(plan.overflow.length).toBeGreaterThan(0)
    expect(plan.overflow.at(-1)).toBe('close')
    // The menu lists them in priority order, and each control is in
    // exactly one place.
    expect(plan.overflow).toEqual(
      CONTROL_PRIORITY.filter((id) => plan.overflow.includes(id))
    )
    for (const id of ALL) {
      expect(plan.shown.has(id)).toBe(!plan.overflow.includes(id))
    }
    // What stays is the most important, in order: a prefix of the list.
    expect([...plan.shown]).toEqual(ALL.slice(0, plan.shown.size))
  })

  it('gives up controls one by one as the bar narrows', () => {
    let previous = Infinity
    for (let width = 1200; width >= 400; width -= 20) {
      const { shown } = planControls(width, ALL)
      expect(shown.size).toBeLessThanOrEqual(previous)
      previous = shown.size
    }
  })

  it('keeps the volume, as a button once even the clock has gone', () => {
    const narrow = planControls(520, ALL)
    expect(narrow.shown.size).toBe(0)
    expect(narrow.overflow).toEqual(ALL)
    expect(narrow.volume).toBe('compact')
  })

  it('only plans controls the track has', () => {
    const plan = planControls(800, ['clock', 'repeat', 'close'])
    expect([...plan.shown, ...plan.overflow].sort()).toEqual(
      ['clock', 'close', 'repeat'].sort()
    )
  })

  it('a phone has no volume or clock, and opens Now playing from the menu', () => {
    const plan = planControls(380, ALL, { phone: true })
    expect(plan.volume).toBe('none')
    expect(plan.shown.has('clock')).toBe(false)
    expect(plan.overflow).not.toContain('clock')
    expect(plan.overflow).toEqual(
      expect.arrayContaining(['nowPlaying', 'lyrics'])
    )
    expect(plan.shown.has('nowPlaying')).toBe(false)
  })

  it('a roomy phone still keeps Now playing and the lyrics in the menu', () => {
    const plan = planControls(1000, ALL, { phone: true })
    expect(plan.overflow).toEqual(['nowPlaying', 'lyrics'])
  })
})
