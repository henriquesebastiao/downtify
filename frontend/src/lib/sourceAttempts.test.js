import { describe, expect, it } from 'vitest'
import {
  attemptReason,
  attemptsOf,
  failureBreakdown,
  shortError,
  sourceLabel,
} from './sourceAttempts'

const t = (key, values) =>
  values && 'count' in values ? `${key}:${values.count}` : key

const SLSKD_MISS = {
  provider: 'slskd',
  result: 'nothing',
  reason: 'no_match',
  detail: '',
}
const YTM_FAILED = {
  provider: 'youtube-music',
  result: 'failed',
  reason: '',
  detail: 'ERROR: [youtube] AbC123xyz09: The page needs to be reloaded. x',
}

describe('sourceAttempts', () => {
  it('labels sources like the source badge', () => {
    expect(sourceLabel('youtube-music')).toBe('YouTube Music')
    expect(sourceLabel('slskd')).toBe('slskd')
    expect(sourceLabel('other')).toBe('other')
  })

  it('reads only well-formed rows', () => {
    expect(attemptsOf({})).toEqual([])
    expect(attemptsOf({ sources: [null, {}, SLSKD_MISS] })).toEqual([
      SLSKD_MISS,
    ])
  })

  it('reuses the slskd reasons and names failures', () => {
    expect(attemptReason(SLSKD_MISS, t)).toBe('slskdMisses.reason.no_match')
    expect(attemptReason(YTM_FAILED, t)).toBe('queue.sourceFailed')
    expect(
      attemptReason({ provider: 'youtube-music', result: 'nothing' }, t)
    ).toBe('queue.sourceNothing')
    expect(attemptReason({ provider: 'x', result: 'rejected' }, t)).toBe(
      'queue.sourceRejected'
    )
  })

  it('drops the per-video part of a yt-dlp error', () => {
    expect(shortError(YTM_FAILED.detail)).toBe('The page needs to be reloaded.')
    expect(shortError('Error: plain failure')).toBe('plain failure')
  })

  it('counts every failed song per source, then per reason', () => {
    const items = [
      { sources: [SLSKD_MISS, YTM_FAILED] },
      {
        sources: [
          { ...SLSKD_MISS, reason: 'no_results' },
          {
            ...YTM_FAILED,
            detail:
              'ERROR: [youtube] Zz9yy8xx7w6: The page needs to be reloaded.',
          },
        ],
      },
      { sources: [] },
    ]

    const rows = failureBreakdown(items, t)

    expect(rows.map((row) => [row.provider, row.count])).toEqual([
      ['slskd', 2],
      ['youtube-music', 2],
      ['none', 1],
    ])
    // The same yt-dlp error on two videos is one reason.
    expect(rows[1].reasons).toEqual([
      {
        text: 'queue.sourceFailed: The page needs to be reloaded.',
        count: 2,
      },
    ])
    expect(rows[0].reasons.map((r) => r.count)).toEqual([1, 1])
  })
})
