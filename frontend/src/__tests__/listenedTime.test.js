import { describe, it, expect } from 'vitest'
import { ListenedTime } from '../lib/listenedTime'

describe('actual listened time', () => {
  it('excludes forward seeks, pauses and suspended timers', () => {
    const time = new ListenedTime()
    time.sample(0, 0, true)
    time.sample(1, 1000, true)
    time.sample(100, 2000, true)
    time.sample(101, 3000, true)
    time.sample(101, 4000, false)
    time.sample(200, 64000, true)
    expect(time.seconds).toBe(2)
    time.sample(201, 65000, true)
    expect(time.seconds).toBe(3)
  })
  it('does not multiply time after a backwards seek', () => {
    const time = new ListenedTime()
    time.sample(20, 0, true)
    time.sample(0, 1000, true)
    time.sample(1, 2000, true)
    expect(time.seconds).toBe(1)
  })
})
