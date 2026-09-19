import { describe, expect, it } from 'vitest'

import en from '../i18n/locales/en.js'
import {
  KNOWN_CODES,
  REQUIRED_FIELDS,
  canTest,
  describeTest,
} from '../lib/connectionTest.js'

const check = (id, status, code = '', detail = '') => ({
  id,
  status,
  code,
  detail,
})

describe('describeTest', () => {
  it('shows nothing before a test has run', () => {
    expect(describeTest(null)).toEqual([])
    expect(describeTest(undefined)).toEqual([])
  })

  it('folds a working connection and login into one "Connected" line', () => {
    const lines = describeTest({
      ok: true,
      server: 'slskd 0.21.4',
      checks: [check('connection', 'ok'), check('auth', 'ok')],
    })

    expect(lines).toEqual([
      { status: 'ok', key: 'connected', params: { server: 'slskd 0.21.4' } },
    ])
  })

  it('lists what else was checked after the connection', () => {
    const lines = describeTest(
      {
        ok: true,
        server: 'slskd 0.21.4',
        checks: [
          check('connection', 'ok'),
          check('auth', 'ok'),
          check('soulseek', 'warn', 'offline', 'Disconnected'),
          check('folder', 'warn', 'missing', '/slskd'),
        ],
      },
      { url: 'http://slskd:5030' }
    )

    expect(lines.map((line) => [line.status, line.key])).toEqual([
      ['ok', 'connected'],
      ['warn', 'soulseek_offline'],
      ['warn', 'folder_missing'],
    ])
    // The message can name what it found and what was tried.
    expect(lines[2].params).toMatchObject({
      detail: '/slskd',
      url: 'http://slskd:5030',
    })
  })

  it('reports a failure as itself, with no "Connected" line', () => {
    const lines = describeTest(
      { ok: false, server: '', checks: [check('connection', 'fail', 'tls')] },
      { url: 'https://nd.example' }
    )

    expect(lines).toHaveLength(1)
    expect(lines[0]).toMatchObject({ status: 'fail', key: 'connection_tls' })
  })

  it('keeps a reached-but-refused server distinct from an unreachable one', () => {
    const lines = describeTest({
      ok: false,
      server: '',
      checks: [check('connection', 'ok'), check('auth', 'fail', 'bad_key')],
    })

    // The connection itself is fine, so only the rejection is shown.
    expect(lines.map((line) => line.key)).toEqual(['auth_bad_key'])
  })

  it('shows a code it does not know generically instead of a raw key', () => {
    const [line] = describeTest({
      ok: false,
      server: '',
      checks: [check('connection', 'fail', 'from_a_newer_backend')],
    })

    expect(line.key).toBe('unknown')
    expect(line.params.code).toBe('connection_from_a_newer_backend')
  })
})

describe('canTest', () => {
  it('needs every required field to hold something', () => {
    const fields = REQUIRED_FIELDS.slskd
    expect(canTest({ base_url: 'http://x', api_key: 'k' }, fields)).toBe(true)
    expect(canTest({ base_url: 'http://x', api_key: '' }, fields)).toBe(false)
    expect(canTest({ base_url: 'http://x' }, fields)).toBe(false)
  })

  it('does not count blanks as a value', () => {
    expect(
      canTest({ base_url: '   ', api_key: 'k' }, REQUIRED_FIELDS.slskd)
    ).toBe(false)
  })

  it('asks Navidrome for its address and login', () => {
    expect(REQUIRED_FIELDS.navidrome).toEqual(['url', 'username', 'password'])
    expect(
      canTest(
        { url: 'http://n', username: 'u', password: '' },
        REQUIRED_FIELDS.navidrome
      )
    ).toBe(false)
  })

  it('is false, not an error, for a missing config', () => {
    expect(canTest(undefined, REQUIRED_FIELDS.slskd)).toBe(false)
  })
})

describe('messages', () => {
  it('has a translation for every code the UI claims to know', () => {
    for (const code of KNOWN_CODES) {
      expect(en.settings.test[code], `settings.test.${code}`).toBeTruthy()
    }
    for (const key of ['connected', 'unknown', 'button', 'testing']) {
      expect(en.settings.test[key], `settings.test.${key}`).toBeTruthy()
    }
  })
})
