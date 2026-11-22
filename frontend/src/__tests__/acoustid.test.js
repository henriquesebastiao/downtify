import { describe, expect, it } from 'vitest'

import {
  acoustidBlocker,
  fingerprinterKey,
  looksLikeKey,
  normalizeAcoustid,
} from '/src/lib/acoustid'

describe('acoustid', () => {
  it('fills in a missing or partial status', () => {
    expect(normalizeAcoustid(null)).toEqual({
      enabled: false,
      keySet: false,
      keyHint: '',
      fingerprinter: '',
      ready: false,
    })
    expect(
      normalizeAcoustid({ enabled: true, key_set: true, key_hint: '••••abcd' })
        .keyHint
    ).toBe('••••abcd')
  })

  it('says what stops a run, in order', () => {
    const status = normalizeAcoustid({})
    expect(acoustidBlocker(status)).toBe('acoustidOff')
    status.enabled = true
    expect(acoustidBlocker(status)).toBe('acoustidNoKey')
    status.keySet = true
    expect(acoustidBlocker(status)).toBe('acoustidNoTool')
    status.fingerprinter = 'ffmpeg'
    expect(acoustidBlocker(status)).toBe('')
  })

  it('names the fingerprint tool', () => {
    expect(fingerprinterKey({ fingerprinter: 'fpcalc' })).toBe(
      'acoustidToolFpcalc'
    )
    expect(fingerprinterKey({ fingerprinter: 'ffmpeg' })).toBe(
      'acoustidToolFfmpeg'
    )
    expect(fingerprinterKey({ fingerprinter: '' })).toBe('acoustidToolMissing')
  })

  it('accepts only key-shaped text', () => {
    expect(looksLikeKey(' AbC-12_x ')).toBe(true)
    expect(looksLikeKey('has space')).toBe(false)
    expect(looksLikeKey('ab')).toBe(false)
    expect(looksLikeKey('')).toBe(false)
  })
})
