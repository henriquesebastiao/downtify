import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { isReactive, watch } from 'vue'

const fixture = vi.hoisted(() => ({
  jobs: [],
  listeners: [],
  api: {
    getQueue: vi.fn(),
    downloadFileURL: (file) => `/media/${file}`,
    onMessage: vi.fn(),
    download: vi.fn(),
    downloadBatch: vi.fn(),
    removeQueueItem: vi.fn(),
    clearQueue: vi.fn(),
    clearCompletedQueue: vi.fn(),
    replaceAudio: vi.fn(),
  },
}))

vi.mock('/src/model/api', () => ({ default: fixture.api }))
vi.mock('/src/model/settings', () => ({
  useSettingsManager: () => ({ settings: { value: { generate_m3u: true } } }),
}))

let model
let tracker
let manager

function job(id, values = {}) {
  return {
    song: {
      song_id: id,
      name: 'Generated track',
      artists: ['Generated artist'],
    },
    status: 'queued',
    progress: 0,
    message: '',
    ...values,
  }
}

function send(message) {
  fixture.listeners[0](message)
}

beforeEach(async () => {
  vi.useFakeTimers()
  vi.resetModules()
  fixture.jobs = []
  fixture.listeners = []
  vi.clearAllMocks()
  fixture.api.getQueue.mockImplementation(async () => ({ data: fixture.jobs }))
  fixture.api.onMessage.mockImplementation((fn) => fixture.listeners.push(fn))
  fixture.api.download.mockResolvedValue({ data: 'generated.mp3' })
  fixture.api.downloadBatch.mockResolvedValue({ data: {} })
  fixture.api.removeQueueItem.mockResolvedValue({})
  fixture.api.clearQueue.mockResolvedValue({})
  fixture.api.clearCompletedQueue.mockResolvedValue({})
  fixture.api.replaceAudio.mockResolvedValue({})
  model = await import('../model/download')
  await model.syncQueueFromServer()
  tracker = model.useProgressTracker()
  manager = model.useDownloadManager()
})

afterEach(() => {
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('queue reconciliation', () => {
  it('publishes a changed batch once and preserves reactive item identities', async () => {
    fixture.jobs = Array.from({ length: 300 }, (_, i) => job(`csv:${i}`))
    const before = tracker.queueVersion.value
    await model.syncQueueFromServer()
    expect(tracker.downloadQueue.value).toHaveLength(300)
    expect(tracker.queueVersion.value).toBe(before + 1)
    const items = tracker.downloadQueue.value.slice()
    fixture.jobs = fixture.jobs.map((row, i) => ({
      ...row,
      position: i + 1,
      message: 'Waiting',
    }))
    await model.syncQueueFromServer()
    expect(tracker.queueVersion.value).toBe(before + 2)
    for (let i = 0; i < items.length; i++) {
      expect(tracker.downloadQueue.value[i]).toBe(items[i])
      expect(tracker.getBySong(fixture.jobs[i].song)).toBe(items[i])
      expect(isReactive(items[i])).toBe(true)
    }
  })

  it('does not publish or replace an unchanged snapshot', async () => {
    fixture.jobs = [
      job('done', { status: 'done', filename: 'done.mp3' }),
      job('waiting', { position: 1 }),
    ]
    await model.syncQueueFromServer()
    const items = tracker.downloadQueue.value
    const before = tracker.queueVersion.value
    const timestamp = items[0].updatedAt
    await model.syncQueueFromServer()
    expect(tracker.downloadQueue.value).toBe(items)
    expect(tracker.queueVersion.value).toBe(before)
    expect(items[0].updatedAt).toBe(timestamp)
    expect(items[0].progress).toBe(100)
  })

  it('reconciles a missed WebSocket update on queue_reload', async () => {
    fixture.jobs = [job('a')]
    await model.syncQueueFromServer()
    const item = tracker.getBySong({ song_id: 'a' })
    const before = tracker.queueVersion.value
    fixture.jobs = [job('a', { status: 'done', filename: 'a.mp3' })]
    send({ type: 'queue_reload' })
    await Promise.resolve()
    expect(tracker.getBySong({ song_id: 'a' })).toBe(item)
    expect(item.state).toBe('done')
    expect(item.web_download_url).toBe('/media/a.mp3')
    expect(tracker.queueVersion.value).toBe(before + 1)
  })

  it('preserves field and status normalization from server snapshots', async () => {
    fixture.jobs = [
      job('a', {
        status: 'downloading',
        progress: 45,
        provider: 'slskd',
        position: 2,
      }),
    ]
    await model.syncQueueFromServer()
    const item = tracker.downloadQueue.value[0]
    expect(item).toMatchObject({ progress: 45, provider: 'slskd', position: 2 })
    fixture.jobs = [job('a', { status: 'error', message: 'Generated failure' })]
    await model.syncQueueFromServer()
    expect(item).toMatchObject({
      progress: 0,
      provider: 'slskd',
      position: null,
      message: 'Generated failure',
    })
    expect(item.state).toBe('failed')
  })

  it('keeps the existing poll interval and stops after terminal jobs', async () => {
    fixture.jobs = [job('a')]
    await model.syncQueueFromServer()
    const calls = fixture.api.getQueue.mock.calls.length
    await vi.advanceTimersByTimeAsync(2999)
    expect(fixture.api.getQueue).toHaveBeenCalledTimes(calls)
    await vi.advanceTimersByTimeAsync(1)
    expect(fixture.api.getQueue).toHaveBeenCalledTimes(calls + 1)
    fixture.jobs = [job('a', { status: 'error' })]
    await model.syncQueueFromServer()
    const finished = fixture.api.getQueue.mock.calls.length
    await vi.advanceTimersByTimeAsync(6000)
    expect(fixture.api.getQueue).toHaveBeenCalledTimes(finished)
  })

  it('retains existing rows after a failed poll', async () => {
    fixture.jobs = [job('a')]
    await model.syncQueueFromServer()
    const items = tracker.downloadQueue.value
    const before = tracker.queueVersion.value
    fixture.api.getQueue.mockRejectedValueOnce(new Error('offline'))
    await expect(model.syncQueueFromServer()).rejects.toThrow('offline')
    expect(tracker.downloadQueue.value).toBe(items)
    expect(tracker.queueVersion.value).toBe(before)
  })

  it('ignores rows without songs and preserves unindexable public rows', async () => {
    fixture.jobs = [{ status: 'done' }]
    await model.syncQueueFromServer()
    expect(tracker.downloadQueue.value).toHaveLength(0)
    tracker.appendSong({})
    expect(tracker.getBySong({})).toBeNull()
    tracker.removeSong({})
    expect(tracker.downloadQueue.value).toHaveLength(0)
  })

  it('does linear key work for an existing generated batch', async () => {
    const count = 300
    let reads = 0
    fixture.jobs = Array.from({ length: count }, (_, i) => ({
      ...job(''),
      song: {
        get song_id() {
          reads++
          return `generated:${i}`
        },
      },
    }))
    await model.syncQueueFromServer()
    reads = 0
    await model.syncQueueFromServer()
    expect(reads).toBeLessThan(count * 8)
  })
})

describe('WebSocket progress', () => {
  it('publishes all changed progress fields and status once', () => {
    const before = tracker.queueVersion.value
    const event = {
      song: { song_id: 'a' },
      status: 'downloading',
      progress: 42,
      message: 'Receiving',
      provider: 'youtube-music',
    }
    send(event)
    expect(tracker.queueVersion.value).toBe(before + 1)
    const item = tracker.getBySong(event.song)
    expect(item).toBe(tracker.downloadQueue.value[0])
    expect(item).toMatchObject({
      progress: 42,
      message: 'Receiving',
      provider: 'youtube-music',
    })
    expect(item.state).toBe('active')
    send(event)
    expect(tracker.queueVersion.value).toBe(before + 1)
  })

  it('immediately publishes success and error without intermediate versions', () => {
    send({ song: { song_id: 'a' }, status: 'downloading', progress: 5 })
    const item = tracker.downloadQueue.value[0]
    const changes = []
    const stop = watch(tracker.downloadQueue, () => changes.push(item.state), {
      flush: 'sync',
    })
    send({
      song: item.song,
      status: 'done',
      filename: 'a.mp3',
      message: 'Done',
    })
    expect(changes).toEqual(['done'])
    expect(item.progress).toBe(100)
    const before = tracker.queueVersion.value
    send({
      song: item.song,
      status: 'done',
      filename: 'a.mp3',
      message: 'Done',
    })
    expect(tracker.queueVersion.value).toBe(before)
    send({ song: item.song, status: 'error', message: 'Generated failure' })
    expect(changes).toEqual(['done', 'failed'])
    stop()
  })

  it('updates the indexed reactive row itself', () => {
    const item = tracker.appendSong({ song_id: 'a' })
    const observed = vi.fn()
    const stop = watch(() => item.progress, observed, { flush: 'sync' })
    send({ song: { song_id: 'a' }, status: 'downloading', progress: 25 })
    expect(observed).toHaveBeenCalledWith(25, 0, expect.anything())
    expect(tracker.getBySong(item.song)).toBe(item)
    stop()
  })
})

describe('queue index lifecycle', () => {
  it('uses the existing identity rules, not track titles', () => {
    const first = tracker.appendSong({
      song_id: ' a ',
      url: 'ignored',
      name: 'Same',
    })
    const second = tracker.appendSong({
      url: ' https://example.test/track ',
      name: 'Same',
    })
    expect(tracker.getBySong({ song_id: 'a' })).toBe(first)
    expect(tracker.getBySong({ url: 'https://example.test/track' })).toBe(
      second
    )
    expect(model.jobSongKey(null)).toBe('')
  })

  it('removes index entries through both removal actions', () => {
    const first = tracker.appendSong({ song_id: 'a' })
    tracker.removeSong(first.song)
    expect(tracker.getBySong(first.song)).toBeNull()
    const second = tracker.appendSong(first.song)
    expect(second).not.toBe(first)
    manager.remove(second.song)
    expect(tracker.getBySong(second.song)).toBeNull()
    expect(fixture.api.removeQueueItem).toHaveBeenCalledWith('a')
  })

  it('does not publish a removal that changes nothing', () => {
    const before = tracker.queueVersion.value
    tracker.removeSong({ song_id: 'missing' })
    expect(tracker.queueVersion.value).toBe(before)
  })

  it('releases completed rows while keeping active and failed items', async () => {
    fixture.jobs = [
      job('done', { status: 'done' }),
      job('active'),
      job('failed', { status: 'error' }),
    ]
    await model.syncQueueFromServer()
    const active = tracker.getBySong({ song_id: 'active' })
    await manager.clearCompleted()
    expect(tracker.getBySong({ song_id: 'done' })).toBeNull()
    expect(tracker.getBySong(active.song)).toBe(active)
    expect(tracker.getBySong({ song_id: 'failed' }).state).toBe('failed')
    await manager.clearAll()
    expect(tracker.downloadQueue.value).toHaveLength(0)
    expect(tracker.getBySong(active.song)).toBeNull()
  })

  it('keeps first-match semantics for duplicate public appends', async () => {
    const first = tracker.appendSong({ song_id: 'a' })
    first.setDownloaded()
    const second = tracker.appendSong({ song_id: 'a' })
    expect(tracker.getBySong(first.song)).toBe(first)
    await manager.clearCompleted()
    expect(tracker.getBySong(second.song)).toBe(second)
  })

  it('retries the same reactive item with an explicitly selected source', async () => {
    const item = tracker.appendSong({ song_id: 'a' })
    item.setError()
    const result = await manager.retryWithAudio(item.song, 'generated-video')
    expect(tracker.downloadQueue.value).toHaveLength(1)
    expect(tracker.getBySong(item.song)).toBe(item)
    expect(item.song.youtube_id).toBe('generated-video')
    expect(fixture.api.download).toHaveBeenCalledWith({
      song_id: 'a',
      youtube_id: 'generated-video',
    })
    expect(result.filename).toBe('generated.mp3')
  })

  it('retries with a SoundCloud track instead of an earlier video', async () => {
    const item = tracker.appendSong({ song_id: 'a', youtube_id: 'old-video' })
    item.setError()
    const url = 'https://soundcloud.com/artist/track'
    await manager.retryWithAudio(item.song, url, 'soundcloud')
    expect(item.song.soundcloud_url).toBe(url)
    expect(item.song.youtube_id).toBeUndefined()
    const sent = fixture.api.download.mock.calls.at(-1)[0]
    expect(sent.soundcloud_url).toBe(url)
    expect(sent.youtube_id).toBeUndefined()
  })

  it('batches resubmitted songs without replacing their items', async () => {
    const item = tracker.appendSong({ song_id: 'a' })
    item.setDownloaded()
    const before = tracker.queueVersion.value
    await manager.fromSongs([{ song_id: 'a' }, { song_id: 'b' }])
    expect(tracker.getBySong(item.song)).toBe(item)
    expect(tracker.downloadQueue.value).toHaveLength(2)
    expect(tracker.queueVersion.value).toBe(before + 1)
    expect(fixture.api.downloadBatch).toHaveBeenCalledTimes(1)
  })

  it('continues retrying audio replacement through its original route', async () => {
    const song = {
      song_id: 'replace:a',
      replace: { file: 'a.mp3', video_id: 'old' },
    }
    const item = tracker.appendSong(song)
    item.setError()
    await manager.retryWithAudio(song, 'new')
    expect(tracker.getBySong(song)).toBe(item)
    expect(fixture.api.replaceAudio).toHaveBeenCalledWith('a.mp3', 'new')
    expect(fixture.api.download).not.toHaveBeenCalled()
  })
})

it('shows a reused file as completed library content without a stale audio-provider badge', () => {
  const song = { song_id: 'reuse-fixture' }
  send({ song, progress: 15, status: 'downloading', provider: 'youtube-music' })
  send({
    song,
    progress: 100,
    status: 'done',
    reused: true,
    message: 'Already downloaded',
    filename: 'existing.mp3',
  })
  const item = tracker.getBySong(song)
  expect(item.state).toBe('done')
  expect(item.provider).toBe('')
  expect(item.message).toBe('Already downloaded')
})
