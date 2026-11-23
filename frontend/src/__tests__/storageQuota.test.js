import { describe, expect, it } from 'vitest'
import {
  GB,
  MODE_CUSTOM,
  MODE_DEFAULT,
  MODE_UNLIMITED,
  UNLIMITED,
  bytesToGb,
  gbToBytes,
  quotaMode,
  quotaPayload,
  quotaPercent,
  quotaTone,
} from '../lib/storageQuota'

describe('storage quota', () => {
  it('converts between bytes and the GB typed in a field', () => {
    expect(bytesToGb(2 * GB)).toBe('2')
    expect(bytesToGb(1.5 * GB)).toBe('1.5')
    expect(bytesToGb(4 * 1024 ** 2)).toBe('0.00391')
    expect(bytesToGb(null)).toBe('')
    expect(bytesToGb(-1)).toBe('')
    expect(gbToBytes('2')).toBe(2 * GB)
    expect(gbToBytes('0,5')).toBe(GB / 2)
    expect(gbToBytes('')).toBeNull()
    expect(gbToBytes('0')).toBeNull()
    expect(gbToBytes('abc')).toBeNull()
  })

  it('reads an account’s own setting as a choice', () => {
    expect(quotaMode(null)).toBe(MODE_DEFAULT)
    expect(quotaMode(undefined)).toBe(MODE_DEFAULT)
    expect(quotaMode(UNLIMITED)).toBe(MODE_UNLIMITED)
    expect(quotaMode(GB)).toBe(MODE_CUSTOM)
  })

  it('turns a choice into what the server takes', () => {
    expect(quotaPayload(MODE_DEFAULT, '3')).toBeNull()
    expect(quotaPayload(MODE_UNLIMITED, '')).toBe(UNLIMITED)
    expect(quotaPayload(MODE_CUSTOM, '3')).toBe(3 * GB)
    expect(quotaPayload(MODE_CUSTOM, '')).toBeUndefined()
  })

  it('says how full an account is', () => {
    const half = { used: GB, limit: 2 * GB, unlimited: false }
    expect(quotaPercent(half)).toBe(50)
    expect(quotaTone(half)).toBe('')
    const nearly = { used: 1.9 * GB, limit: 2 * GB, unlimited: false }
    expect(quotaTone(nearly)).toBe('warn')
    const full = { used: 3 * GB, limit: 2 * GB, exceeded: true }
    expect(quotaPercent(full)).toBe(100)
    expect(quotaTone(full)).toBe('danger')
    const free = { used: 5 * GB, limit: null, unlimited: true }
    expect(quotaPercent(free)).toBe(0)
    expect(quotaTone(free)).toBe('')
  })
})
