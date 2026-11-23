import { describe, expect, it, vi } from 'vitest'
import { motionDuration, popoverOrigin } from '../lib/motion.js'
import { createRouteProgress, trickle } from '../lib/routeProgress.js'
import {
  prefetchRoutes,
  routeLoaders,
  shouldPrefetch,
} from '../lib/prefetch.js'

describe('motionDuration', () => {
  it('tells a transition how long its children take', () => {
    expect(motionDuration(false, 420, 300)).toEqual({ enter: 420, leave: 300 })
    expect(motionDuration(false, 200)).toEqual({ enter: 200, leave: 200 })
  })

  it('waits for nothing when less motion is asked for', () => {
    expect(motionDuration(true, 420, 300)).toBe(0)
  })
})

describe('popoverOrigin', () => {
  const trigger = { left: 300, top: 100, width: 40, height: 40 }

  it('grows a menu below its trigger from the corner under it', () => {
    // Aligned with the trigger's end: the top right corner.
    const menu = { left: 132, top: 146, width: 208, height: 200 }
    expect(popoverOrigin(menu, trigger)).toBe('top right')
    // Aligned with its start: the top left corner.
    const start = { left: 300, top: 146, width: 208, height: 200 }
    expect(popoverOrigin(start, trigger)).toBe('top left')
  })

  it('grows a menu flipped above its trigger from the bottom', () => {
    const menu = { left: 132, top: 0, width: 208, height: 94 }
    expect(popoverOrigin(menu, trigger)).toBe('bottom right')
  })

  it('grows a right-click menu from the pointer', () => {
    const pointer = { left: 400, top: 300, width: 0, height: 0 }
    const menu = { left: 400, top: 306, width: 208, height: 200 }
    expect(popoverOrigin(menu, pointer)).toBe('top left')
    // Pushed left by the window's edge: from where the pointer is.
    const pushed = { left: 300, top: 306, width: 208, height: 200 }
    expect(popoverOrigin(pushed, pointer)).toBe('top 100px')
  })
})

function fakeTimers() {
  let now = 0
  let id = 0
  const pending = new Map()
  const add = (fn, ms, every) => {
    id += 1
    pending.set(id, { fn, at: now + ms, every })
    return id
  }
  return {
    setTimeout: (fn, ms) => add(fn, ms, 0),
    setInterval: (fn, ms) => add(fn, ms, ms),
    clearTimeout: (key) => pending.delete(key),
    clearInterval: (key) => pending.delete(key),
    advance(ms) {
      const end = now + ms
      for (;;) {
        const due = [...pending.entries()]
          .filter(([, t]) => t.at <= end)
          .sort((a, b) => a[1].at - b[1].at)[0]
        if (!due) break
        const [key, timer] = due
        now = timer.at
        if (timer.every) timer.at += timer.every
        else pending.delete(key)
        timer.fn()
      }
      now = end
    },
  }
}

describe('route progress', () => {
  it('slows down near its cap and never passes it', () => {
    let value = 0.1
    for (let i = 0; i < 200; i += 1) value = trickle(value)
    expect(value).toBeLessThan(0.9)
    expect(value).toBeGreaterThan(0.89)
  })

  it('shows nothing for a page that comes quickly', () => {
    const timers = fakeTimers()
    const onChange = vi.fn()
    const bar = createRouteProgress({ onChange, timers })
    bar.start()
    timers.advance(100)
    bar.done()
    timers.advance(2000)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('grows while a page is on its way, then fills and fades', () => {
    const timers = fakeTimers()
    const bar = createRouteProgress({ timers })
    bar.start()
    timers.advance(150)
    expect(bar.state).toEqual({ visible: true, value: 0.1 })
    timers.advance(1000)
    expect(bar.state.value).toBeGreaterThan(0.1)
    expect(bar.state.value).toBeLessThan(0.9)
    bar.done()
    expect(bar.state).toEqual({ visible: true, value: 1 })
    timers.advance(260)
    expect(bar.state.visible).toBe(false)
    timers.advance(400)
    expect(bar.state).toEqual({ visible: false, value: 0 })
  })

  it('starts a new bar from nothing while the last one fades', () => {
    const timers = fakeTimers()
    const bar = createRouteProgress({ timers })
    bar.start()
    timers.advance(500)
    bar.done()
    bar.start()
    expect(bar.state).toEqual({ visible: false, value: 0 })
    timers.advance(150)
    expect(bar.state).toEqual({ visible: true, value: 0.1 })
  })
})

describe('prefetching pages', () => {
  it('stays off on a connection that saves data or is slow', () => {
    expect(shouldPrefetch(undefined)).toBe(true)
    expect(shouldPrefetch({ effectiveType: '4g' })).toBe(true)
    expect(shouldPrefetch({ saveData: true, effectiveType: '4g' })).toBe(false)
    expect(shouldPrefetch({ effectiveType: '2g' })).toBe(false)
    expect(shouldPrefetch({ effectiveType: 'slow-2g' })).toBe(false)
  })

  it('takes the lazy routes asked for, in that order', () => {
    const library = () => {}
    const queue = () => {}
    const routes = [
      { name: 'Home', components: { default: { name: 'HomeView' } } },
      { name: 'Queue', components: { default: queue } },
      { name: 'Library', components: { default: library } },
    ]
    expect(routeLoaders(routes, ['Library', 'Home', 'Gone', 'Queue'])).toEqual([
      library,
      queue,
    ])
  })

  it('loads them one at a time, extras first, a failure not stopping it', async () => {
    const order = []
    const load =
      (name, fail = false) =>
      () => {
        order.push(name)
        return fail ? Promise.reject(new Error(name)) : Promise.resolve()
      }
    const router = {
      getRoutes: () => [
        { name: 'Library', components: { default: load('library', true) } },
        { name: 'Queue', components: { default: load('queue') } },
      ],
    }
    const scheduled = []
    prefetchRoutes(router, ['Library', 'Queue'], {
      extra: [load('now-playing')],
      schedule: (fn) => scheduled.push(fn),
    })
    while (scheduled.length) {
      scheduled.shift()()
      await new Promise((resolve) => setTimeout(resolve, 0))
    }
    expect(order).toEqual(['now-playing', 'library', 'queue'])
  })
})
