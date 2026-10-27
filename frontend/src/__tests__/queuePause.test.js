import { beforeEach, describe, expect, it, vi } from 'vitest'

const fixture = vi.hoisted(() => ({
  listeners: [],
  api: {
    getQueueState: vi.fn(),
    pauseQueue: vi.fn(),
    resumeQueue: vi.fn(),
    onMessage: vi.fn(),
  },
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))

const RUNNING = { paused: false, state: 'running', active: 0 }

let queuePause

beforeEach(async () => {
  vi.resetModules()
  vi.clearAllMocks()
  fixture.listeners = []
  fixture.api.onMessage.mockImplementation((fn) => fixture.listeners.push(fn))
  fixture.api.getQueueState.mockResolvedValue({ data: RUNNING })
  const model = await import('../model/queuePause')
  queuePause = model.useQueuePause()
  await model.refreshQueueState()
})

describe('queue pause switch', () => {
  it('starts from the server state', async () => {
    fixture.api.getQueueState.mockResolvedValue({
      data: { paused: true, state: 'paused', active: 0 },
    })

    await queuePause.refresh()

    expect(queuePause.paused.value).toBe(true)
    expect(queuePause.draining.value).toBe(false)
  })

  it('reads pausing while running downloads finish', async () => {
    fixture.api.pauseQueue.mockResolvedValue({
      data: { paused: true, state: 'pausing', active: 2 },
    })

    await queuePause.pause()

    expect(fixture.api.pauseQueue).toHaveBeenCalledOnce()
    expect(queuePause.paused.value).toBe(true)
    expect(queuePause.draining.value).toBe(true)
    expect(queuePause.status.active).toBe(2)
    expect(queuePause.busy.value).toBe(false)
  })

  it('follows queue_state frames from the server', () => {
    fixture.listeners[0]({ type: 'queue_state', paused: true, active: 0 })
    expect(queuePause.status.state).toBe('paused')

    fixture.listeners[0]({ type: 'queue_reload' })
    expect(queuePause.paused.value).toBe(true)

    fixture.listeners[0]({ type: 'queue_state', ...RUNNING })
    expect(queuePause.paused.value).toBe(false)
  })

  it('resumes', async () => {
    fixture.api.resumeQueue.mockResolvedValue({ data: RUNNING })
    fixture.listeners[0]({ type: 'queue_state', paused: true })

    await queuePause.resume()

    expect(fixture.api.resumeQueue).toHaveBeenCalledOnce()
    expect(queuePause.paused.value).toBe(false)
  })

  it('stays usable when the request fails', async () => {
    fixture.api.pauseQueue.mockRejectedValue(new Error('offline'))

    await expect(queuePause.pause()).rejects.toThrow('offline')

    expect(queuePause.busy.value).toBe(false)
    expect(queuePause.paused.value).toBe(false)
  })
})
