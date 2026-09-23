import { describe, expect, it, vi } from 'vitest'

const { listeners, getQueue, jobs } = vi.hoisted(() => {
  const jobs = Array.from({ length: 300 }, (_, i) => ({
    song: { song_id: `csv:${i}`, name: `Song ${i}`, artists: ['Artist'] },
    status: 'queued',
    progress: 0,
    message: '',
  }))
  return {
    jobs,
    listeners: [],
    getQueue: vi.fn(async () => ({ data: jobs })),
  }
})

vi.mock('/src/model/api', () => ({
  default: {
    onMessage(fn) {
      listeners.push(fn)
      return () => {}
    },
    getQueue,
    getSettings: () => Promise.resolve({ data: {} }),
    downloadFileURL: (name) => name,
  },
}))

import { syncQueueFromServer, useProgressTracker } from '../model/download'

describe('syncQueueFromServer', () => {
  it('bumps the queue version once for a few hundred jobs', async () => {
    await syncQueueFromServer()
    const { queueVersion, downloadQueue } = useProgressTracker()
    const before = queueVersion.value
    await syncQueueFromServer()
    expect(downloadQueue.value).toHaveLength(jobs.length)
    expect(queueVersion.value).toBe(before + 1)
  })

  it('reloads once when the server sends queue_reload', async () => {
    await syncQueueFromServer()
    const { queueVersion } = useProgressTracker()
    const before = queueVersion.value
    expect(listeners).toHaveLength(1)
    listeners[0]({ type: 'queue_reload' })
    await vi.waitFor(() => {
      expect(queueVersion.value).toBe(before + 1)
    })
  })
})
