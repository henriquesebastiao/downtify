import { describe, expect, it } from 'vitest'
import { restoreParams, restoreSummary } from '/src/lib/backups'
import en from '/src/i18n/locales/en.js'

function t(key, params = {}) {
  const [group, name] = key.split('.')
  return String(en[group][name]).replace(/\{(\w+)\}/g, (_, k) => params[k])
}

describe('backups', () => {
  it('sends what to restore as query flags', () => {
    expect(restoreParams({ settings: true, watches: false })).toEqual({
      settings: '1',
      watches: '0',
      songs: '0',
    })
  })

  it('says what a restore did', () => {
    expect(
      restoreSummary(
        {
          settings: ['max_parallel_downloads'],
          watches_added: 3,
          watches_present: 1,
          songs_checked: true,
          songs_missing: 40,
          songs_queued: 40,
        },
        t
      )
    ).toBe(
      'Settings restored · 3 watches added, 1 already here · 40 songs missing, 40 queued for download'
    )
  })

  it('says when no songs were missing, only when songs were checked', () => {
    const base = { settings: [], watches_added: 0, songs_missing: 0 }
    expect(restoreSummary({ ...base, songs_checked: true }, t)).toBe(
      'No songs were missing'
    )
    expect(restoreSummary({ ...base, songs_checked: false }, t)).toBe('')
    expect(restoreSummary(null, t)).toBe('')
  })
})
