import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'

const api = vi.hoisted(() => ({
  navidromeRatingsStatus: vi.fn(),
  navidromeRatingsRun: vi.fn(),
  navidromeRatingsCancel: vi.fn(),
}))
vi.mock('/src/model/api', () => ({ default: api }))

import NavidromeRatings from '../components/settings/NavidromeRatings.vue'
import { setLocale } from '../i18n'
import {
  describeRatings,
  useNavidromeRatings,
} from '../lib/navidromeRatings.js'

const OPTIONS = {
  repeat: 'off',
  skip_rated: true,
  skip_starred: false,
  grading: 'absolute',
}

const job = (extra = {}) => ({
  id: 'j1',
  state: 'running',
  trigger: 'manual',
  preview: false,
  started_at: '2026-05-01T10:00:00Z',
  finished_at: null,
  progress: { done: 0, total: 0, step: 'library' },
  result: null,
  error: null,
  ...extra,
})
const finished = (extra = {}) =>
  job({
    state: 'done',
    finished_at: '2026-05-01T10:05:00Z',
    progress: { done: 10, total: 10, step: 'rating' },
    result: {
      state: 'done',
      preview: false,
      total: 10,
      rated: 7,
      skipped: 2,
      not_found: 1,
      changes: [],
      unmatched: [],
    },
    ...extra,
  })
const previewRun = () =>
  finished({
    preview: true,
    result: {
      state: 'done',
      preview: true,
      total: 4,
      rated: 2,
      skipped: 1,
      not_found: 1,
      changes: [
        {
          artist: 'Some Band',
          album: 'Album',
          title: 'Big Hit',
          rank: 1234567,
          stars: 5,
          was: 0,
        },
      ],
      unmatched: ['Nobody – Nothing – Lost Song'],
    },
  })
const status = (data) =>
  api.navidromeRatingsStatus.mockResolvedValue({
    data: { job: null, last: null, next_run_at: null, ...data },
  })

beforeEach(() => {
  vi.useFakeTimers()
  setLocale('en')
  status({})
  api.navidromeRatingsRun.mockResolvedValue({ data: job() })
  api.navidromeRatingsCancel.mockResolvedValue({ data: {} })
})
afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('useNavidromeRatings', () => {
  let ratings
  const open = async (options = OPTIONS) => {
    ratings = useNavidromeRatings(() => options)
    await ratings.refresh()
    return ratings
  }
  afterEach(() => ratings?.dispose())

  it('runs with the current options', async () => {
    await open()
    await ratings.start(false)
    expect(api.navidromeRatingsRun).toHaveBeenCalledWith({
      preview: false,
      ...OPTIONS,
    })
  })

  it('preview sends preview true', async () => {
    await open()
    await ratings.start(true)
    expect(api.navidromeRatingsRun).toHaveBeenCalledWith({
      preview: true,
      ...OPTIONS,
    })
  })

  it('ignores a second start while the first is in flight', async () => {
    let finish
    api.navidromeRatingsRun.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve
      })
    )
    await open()
    const first = ratings.start(false)
    expect(ratings.starting.value).toBe(true)
    await ratings.start(true)
    expect(api.navidromeRatingsRun).toHaveBeenCalledTimes(1)
    finish({ data: job({ id: 'posted' }) })
    await first
    expect(ratings.starting.value).toBe(false)
    expect(api.navidromeRatingsRun).toHaveBeenCalledTimes(1)
  })

  it('clears the guard when the start fails', async () => {
    await open()
    api.navidromeRatingsRun.mockRejectedValueOnce(new Error('Network down'))
    await ratings.start(false)
    expect(ratings.starting.value).toBe(false)
    await ratings.start(false)
    expect(api.navidromeRatingsRun).toHaveBeenCalledTimes(2)
  })

  it('shows the job from the start reply before the refresh answers', async () => {
    await open()
    let answer
    api.navidromeRatingsStatus.mockReturnValueOnce(
      new Promise((resolve) => {
        answer = resolve
      })
    )
    const started = ratings.start(false)
    await vi.waitFor(() => expect(ratings.view.value.running).toBe(true))
    answer({ data: { job: job(), last: null, next_run_at: null } })
    await started
  })

  it('looks again right after a start and a stop', async () => {
    await open()
    await ratings.start(false)
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(2)
    await ratings.stop()
    expect(api.navidromeRatingsCancel).toHaveBeenCalledOnce()
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(3)
  })

  it('polls every 1.5 s while running and every 15 s otherwise', async () => {
    status({ job: job() })
    await open()
    await vi.advanceTimersByTimeAsync(1500)
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(2)
    status({})
    await vi.advanceTimersByTimeAsync(1500)
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(3)
    await vi.advanceTimersByTimeAsync(14000)
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(3)
    await vi.advanceTimersByTimeAsync(1000)
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(4)
  })

  it('stops polling once disposed, even mid-request', async () => {
    await open()
    ratings.dispose()
    await vi.advanceTimersByTimeAsync(60000)
    expect(api.navidromeRatingsStatus).toHaveBeenCalledTimes(1)
  })

  it('explains why a run could not start', async () => {
    await open()
    api.navidromeRatingsRun.mockRejectedValueOnce({
      response: { data: { detail: { code: 'navidrome_not_configured' } } },
    })
    await ratings.start(false)
    expect(ratings.runError.value).toBe('Save the Navidrome login first.')
    api.navidromeRatingsRun.mockRejectedValueOnce({
      response: { data: { detail: { code: 'ratings_busy' } } },
    })
    await ratings.start(false)
    expect(ratings.runError.value).toBe('A ratings run is already going.')
    api.navidromeRatingsRun.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Library-only mode is on' } },
    })
    await ratings.start(false)
    expect(ratings.runError.value).toBe('Library-only mode is on')
    api.navidromeRatingsRun.mockRejectedValueOnce(new Error('Network down'))
    await ratings.start(false)
    expect(ratings.runError.value).toBe('The ratings run failed: Network down')
    api.navidromeRatingsRun.mockResolvedValueOnce({ data: job() })
    await ratings.start(false)
    expect(ratings.runError.value).toBe('')
  })
})

describe('describeRatings', () => {
  const view = (state) =>
    describeRatings({ job: null, last: null, nextRunAt: null, ...state })

  it('shows progress while running', () => {
    const rating = view({
      job: job({ progress: { done: 1200, total: 3400, step: 'rating' } }),
    })
    expect(rating.running).toBe(true)
    expect(rating.progressText).toBe('1,200 of 3,400 songs')
    expect(rating.indeterminate).toBe(false)
    expect(Math.round(rating.percent)).toBe(35)
  })

  it('says it is reading the library first', () => {
    const reading = view({ job: job() })
    expect(reading.progressText).toBe('Reading your Navidrome library…')
    expect(reading.indeterminate).toBe(true)
  })

  it('says it is reading before the first progress report', () => {
    const fresh = view({
      job: job({ progress: { done: 0, total: 0, step: '' } }),
    })
    expect(fresh.progressText).toBe('Reading your Navidrome library…')
    expect(fresh.indeterminate).toBe(true)
  })

  it('shows the last result and a preview table', () => {
    const shown = view({ last: previewRun() })
    expect(shown.running).toBe(false)
    expect(shown.lastText).toContain(
      'would be rated, 1 skipped, 1 not found on Deezer'
    )
    expect(shown.changes).toHaveLength(1)
    expect(shown.unmatched).toEqual(['Nobody – Nothing – Lost Song'])
    expect(shown.unmatchedCount).toBe(1)
  })

  it('lists no changes after a real run', () => {
    const shown = view({ last: finished() })
    expect(shown.lastText).toContain('7 rated, 2 skipped, 1 not found')
    expect(shown.lastText).not.toContain('Stopped')
    expect(shown.changes).toEqual([])
  })

  it('marks a stopped run', () => {
    expect(view({ last: finished({ state: 'stopped' }) }).lastText).toContain(
      'Stopped'
    )
  })

  it('says when nothing has run yet', () => {
    expect(view({}).lastText).toBe('Not run yet')
  })

  it('shows the error text for each failure code', () => {
    const failed = (code) =>
      view({
        last: finished({
          state: 'failed',
          result: null,
          error: { code, message: 'boom' },
        }),
      }).lastError
    expect(failed('deezer_unreachable')).toBe(
      "Deezer didn't answer for several minutes. Stars already given are kept, and the next run carries on where this one stopped."
    )
    expect(failed('navidrome_failed')).toBe('Navidrome error: boom')
    expect(failed('ratings_failed')).toBe('The ratings run failed: boom')
  })

  it('says how many preview songs are shown when the list is cut', () => {
    const cut = previewRun()
    cut.result.rated = 1200
    expect(view({ last: cut }).changesTruncated).toBe(true)
    const whole = previewRun()
    whole.result.rated = 1
    expect(view({ last: whole }).changesTruncated).toBe(false)
  })

  it('promises no next run while a run is going', () => {
    const now = Date.parse('2026-05-01T12:00:00Z')
    const next = (state) => describeRatings(state, now).nextText
    const nextRunAt = '2026-05-02T03:00:00Z'
    expect(next({ nextRunAt })).toMatch(/^Next run /)
    expect(next({ nextRunAt, job: job() })).toBe('')
  })

  it('words the next run by how far away it is', () => {
    const now = Date.parse('2026-05-01T12:00:00Z')
    const next = (nextRunAt) => describeRatings({ nextRunAt }, now).nextText
    expect(next(null)).toBe('')
    expect(next('1970-01-01T00:00:00Z')).toBe('Next run within the hour')
    expect(next('2026-05-01T11:00:00Z')).toBe('Next run within the hour')
    expect(next('2026-05-02T03:00:00Z')).toMatch(/^Next run .*2026/)
  })
})

describe('NavidromeRatings', () => {
  it('renders the Run now and Preview buttons', async () => {
    const html = await renderToString(
      createSSRApp(NavidromeRatings, { options: OPTIONS })
    )
    expect(html).toContain('Run now')
    expect(html).toContain('Preview')
    expect(html).toContain('Not run yet')
    expect(html).not.toContain('Stop')
  })
})
