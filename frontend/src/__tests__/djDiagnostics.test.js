import { describe, expect, it, vi } from 'vitest'
import { createDjDiagnostics } from '../model/djDiagnostics'

function fixture() {
  let active = true,
    clock = 1000
  const report = vi.fn()
  const position = vi.fn(() => 123)
  const media = {
    currentTime: 12,
    playbackRate: 1,
    paused: false,
    seeking: false,
    readyState: 4,
    src: '/private-session-secret',
    buffered: { length: 1, start: () => 0, end: () => 30 },
  }
  const diagnostic = createDjDiagnostics({
    enabled: () => active,
    media,
    position,
    now: () => clock,
    report,
  })
  return {
    diagnostic,
    report,
    position,
    media,
    retire: () => {
      active = false
    },
    advance: (ms) => {
      clock += ms
    },
  }
}

describe('admin DJ validation diagnostics', () => {
  it('does not turn a phase measurement omitted by an older API into a measured zero', () => {
    const f = fixture()
    f.diagnostic.receipt(
      { total_interruptions: 0, continuous_seconds: 30 },
      900
    )
    expect(f.report.mock.calls[0][0]).toMatchObject({
      phase_error_seconds: null,
      continuous_seconds: 30,
    })
  })
  it('reports actual buffer, speed and interruption type without source data', () => {
    const f = fixture()
    f.diagnostic.interruption('waiting')
    expect(f.report).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'event',
        event: 'waiting',
        audio_seconds: 12,
        mix_seconds: 123,
        buffered_seconds: 18,
        playback_rate: 1,
        events: { waiting: 1, seeking: 0, pause: 0 },
      })
    )
    expect(JSON.stringify(f.report.mock.calls)).not.toContain(
      'private-session-secret'
    )
  })
  it('does no reads or logging after its owner generation is retired', () => {
    const f = fixture()
    f.retire()
    f.diagnostic.interruption('pause')
    f.diagnostic.stream({ kind: 'error' })
    f.diagnostic.receipt({}, 0)
    expect(f.position).not.toHaveBeenCalled()
    expect(f.report).not.toHaveBeenCalled()
  })
  it('filters raw errors and URLs, and bounds repetitive errors', () => {
    const f = fixture()
    const error = {
      type: 'networkError',
      detail: 'https://private-secret',
      fatal: true,
      http_status: 503,
      url: '/private-secret',
      error: new Error('private-secret'),
    }
    f.diagnostic.stream({ kind: 'error', error })
    f.diagnostic.stream({ kind: 'error', error })
    expect(f.report).toHaveBeenCalledTimes(1)
    expect(f.report.mock.calls[0][0]).toMatchObject({
      type: 'networkError',
      detail: 'unknown',
      fatal: true,
    })
    expect(JSON.stringify(f.report.mock.calls)).not.toContain('private-secret')
  })
  it('separates receipt latency and phase drift and emits again only on reset or cadence', () => {
    const f = fixture()
    const receipt = {
      total_interruptions: 0,
      clock_delta_seconds: -1.4,
      continuous_seconds: 42,
      reset_counts: { clock_drift: 0, 'private-secret': 9 },
      session: 'private-secret',
    }
    f.diagnostic.receipt(receipt, 900)
    f.diagnostic.receipt(receipt, 900)
    expect(f.report).toHaveBeenCalledTimes(1)
    expect(f.report.mock.calls[0][0]).toMatchObject({
      rtt_ms: 100,
      phase_error_seconds: -1.4,
    })
    f.advance(1000)
    f.diagnostic.receipt({ ...receipt, total_interruptions: 1 }, 1900)
    expect(f.report).toHaveBeenCalledTimes(2)
    expect(JSON.stringify(f.report.mock.calls)).not.toContain('private-secret')
  })
})
