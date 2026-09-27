import { describe, expect, it } from 'vitest'
import {
  formatCountdown,
  needsSignIn,
  pairingUri,
  qrPath,
} from '../lib/auth.js'

describe('needsSignIn', () => {
  it('only when sign-in is required and this browser is not signed in', () => {
    expect(needsSignIn({ require_sign_in: true, signed_in: false })).toBe(true)
    expect(needsSignIn({ require_sign_in: true, signed_in: true })).toBe(false)
    expect(needsSignIn({ require_sign_in: false, signed_in: false })).toBe(
      false
    )
    expect(needsSignIn(null)).toBe(false)
  })
})

describe('pairingUri', () => {
  it('carries the address, the server id and the code', () => {
    const uri = pairingUri({
      origin: 'http://192.168.1.20:8000/',
      serverId: 'abc123',
      code: 'K7QM-2XPD',
    })
    expect(uri).toBe(
      'downtify://pair?url=http%3A%2F%2F192.168.1.20%3A8000&sid=abc123&code=K7QM-2XPD'
    )
    const parsed = new URL(uri)
    expect(parsed.searchParams.get('url')).toBe('http://192.168.1.20:8000')
  })
})

describe('qrPath', () => {
  it('draws one square per dark module on a square grid', () => {
    const { size, d } = qrPath('downtify://pair?code=K7QM-2XPD')
    expect(size).toBeGreaterThanOrEqual(21)
    expect(d).toMatch(/^M\d+ \d+h1v1h-1z/)
    // The top-left finder pattern starts dark.
    expect(d.startsWith('M0 0h1v1h-1z')).toBe(true)
  })
})

describe('formatCountdown', () => {
  it('shows minutes and seconds', () => {
    expect(formatCountdown(300)).toBe('5:00')
    expect(formatCountdown(125)).toBe('2:05')
    expect(formatCountdown(-3)).toBe('0:00')
    expect(formatCountdown('x')).toBe('0:00')
  })
})
