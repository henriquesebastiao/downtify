import { describe, expect, it } from 'vitest'
import {
  formatCountdown,
  needsSignIn,
  pairingUri,
  playbackReport,
  qrPath,
  settingsSectionsFor,
} from '../lib/auth.js'
import { ACTIVITY_KINDS, activityIcon } from '../lib/activity.js'

describe('needsSignIn', () => {
  it('whenever the server says this browser is not signed in', () => {
    expect(needsSignIn({ signed_in: false })).toBe(true)
    expect(needsSignIn({ signed_in: true })).toBe(false)
    // An unreachable server doesn't lock the page.
    expect(needsSignIn(null)).toBe(false)
  })
})

describe('settingsSectionsFor', () => {
  const sections = [
    { id: 'general' },
    { id: 'sources', admin: true },
    { id: 'users', admin: true },
    { id: 'apps' },
    { id: 'about' },
  ]

  it('shows an admin everything', () => {
    expect(settingsSectionsFor('admin', sections)).toEqual(sections)
  })

  it('shows a user General, Apps and About', () => {
    expect(settingsSectionsFor('user', sections).map((s) => s.id)).toEqual([
      'general',
      'apps',
      'about',
    ])
    expect(settingsSectionsFor(undefined, sections)).toHaveLength(3)
  })

  it('hides the accounts sections when accounts are turned off', () => {
    const withUsers = sections.map((s) =>
      s.id === 'users' ? { ...s, accounts: true } : s
    )
    const ids = settingsSectionsFor('admin', withUsers, {
      authDisabled: true,
    }).map((s) => s.id)
    expect(ids).toEqual(['general', 'sources', 'apps', 'about'])
    expect(settingsSectionsFor('admin', withUsers)).toHaveLength(5)
  })
})

describe('playbackReport', () => {
  const track = {
    file: 'Portishead - Roads.flac',
    title: 'Roads',
    artists: ['Portishead'],
    album: 'Dummy',
    duration: 305.2,
  }

  it('describes the song for the Activity page', () => {
    expect(
      playbackReport(track, { player: 'tab', state: 'playing', position: 12.7 })
    ).toEqual({
      player: 'tab',
      state: 'playing',
      position: 13,
      track: {
        file: 'Portishead - Roads.flac',
        title: 'Roads',
        artist: 'Portishead',
        album: 'Dummy',
        duration: 305.2,
      },
    })
  })

  it('skips podcasts and nothing, but always reports a stop', () => {
    expect(
      playbackReport({ ...track, isPodcast: true }, { state: 'playing' })
    ).toBeNull()
    expect(playbackReport(null, { state: 'paused' })).toBeNull()
    expect(playbackReport(null, { player: 'tab', state: 'stopped' })).toEqual({
      player: 'tab',
      state: 'stopped',
      track: {},
      position: 0,
    })
  })
})

describe('activity kinds', () => {
  it('has an icon for every kind', () => {
    for (const kind of ACTIVITY_KINDS)
      expect(activityIcon(kind)).not.toBe('activity')
    expect(activityIcon('something-new')).toBe('activity')
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
