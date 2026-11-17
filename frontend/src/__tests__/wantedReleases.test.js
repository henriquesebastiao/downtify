import { describe, expect, it } from 'vitest'
import {
  TYPES,
  filterWanted,
  jobText,
  summary,
  uncheckedNames,
} from '../lib/wantedReleases.js'

const release = (name, section = 'album', extra = {}) => ({
  id: name,
  name,
  section,
  state: 'missing',
  ...extra,
})

const artist = (name, releases, unread = 0, id = name) => ({
  watch: { id, name },
  releases,
  missing: { tracks: 0, releases: releases.length, unread },
  checking: false,
})

const artists = [
  artist('Beyoncé', [release('Lemonade'), release('Renaissance')]),
  artist('Drake', [release('Views'), release('Scary Hours', 'ep')]),
  artist('Unread Act', [], 3),
  artist('Unread With Known', [release('Known Single', 'single')], 2),
]

// Echoes the key and params so the wording stays a locale concern.
const t = (key, params = {}) =>
  `${key}${Object.keys(params).length ? JSON.stringify(params) : ''}`

describe('wanted releases', () => {
  it('lists the release types in display order', () => {
    expect(TYPES).toEqual(['album', 'ep', 'single', 'mixtape', 'other'])
  })

  it('returns everything without a query or type', () => {
    expect(filterWanted(artists, {})).toEqual(artists)
    expect(filterWanted(artists, { query: '  ', type: '' })).toEqual(artists)
  })

  it('filters by release name, ignoring case and accents', () => {
    const out = filterWanted(artists, { query: 'LEMON' })
    expect(out.map((a) => a.watch.name)).toEqual(['Beyoncé'])
    expect(out[0].releases.map((r) => r.name)).toEqual(['Lemonade'])
  })

  it('a query matching the artist keeps all its releases', () => {
    const out = filterWanted(artists, { query: 'beyonce' })
    expect(out).toHaveLength(1)
    expect(out[0].releases).toHaveLength(2)
  })

  it('filters by type through the release section', () => {
    const out = filterWanted(artists, { type: 'ep' })
    const names = out.map((a) => a.watch.name)
    expect(names).toContain('Drake')
    expect(names).not.toContain('Beyoncé')
    expect(out.find((a) => a.watch.name === 'Drake').releases).toEqual([
      release('Scary Hours', 'ep'),
    ])
  })

  it('keeps artists that are not checked yet, even with nothing shown', () => {
    const out = filterWanted(artists, { type: 'ep' })
    expect(out.map((a) => a.watch.name)).toContain('Unread Act')
    expect(
      filterWanted(artists, { query: 'unread' }).map((a) => a.watch.name)
    ).toEqual(['Unread Act', 'Unread With Known'])
    expect(filterWanted(artists, { query: 'zzz' })).toEqual([])
  })

  it('combines query and type', () => {
    const out = filterWanted(artists, { query: 'drake', type: 'album' })
    const drake = out.find((a) => a.watch.name === 'Drake')
    expect(drake.releases.map((r) => r.name)).toEqual(['Views'])
  })

  it('summarises the totals', () => {
    expect(
      summary({ tracks: 12, releases: 4, artists: 2, unchecked: 1 })
    ).toEqual({ tracks: 12, releases: 4, unchecked: 1 })
    expect(summary(null)).toEqual({ tracks: 0, releases: 0, unchecked: 0 })
  })

  it('names the artists not checked yet', () => {
    expect(uncheckedNames(artists)).toEqual(['Unread Act', 'Unread With Known'])
    expect(uncheckedNames([])).toEqual([])
  })

  describe('jobText', () => {
    it('is empty without a job', () => {
      expect(jobText(null, t)).toBe('')
    })

    it('reads a running check', () => {
      const job = { kind: 'check', running: true, done: 2, total: 5 }
      expect(jobText({ ...job, current: 'Drake' }, t)).toBe(
        'monitor.wantedChecking' +
          JSON.stringify({ done: 2, total: 5, name: 'Drake' })
      )
    })

    it('reads a running download', () => {
      const job = {
        kind: 'download',
        running: true,
        done: 0,
        total: 3,
        current: 'Beyoncé',
      }
      expect(jobText(job, t)).toBe(
        'monitor.wantedDownloading' +
          JSON.stringify({ done: 0, total: 3, name: 'Beyoncé' })
      )
    })

    it('reads a finished job with failed, skipped and stopped parts', () => {
      const job = {
        kind: 'download',
        running: false,
        done: 4,
        total: 6,
        failed: 1,
        skipped: 2,
        stopped: true,
      }
      expect(jobText(job, t)).toBe(
        [
          'monitor.wantedFinished' + JSON.stringify({ done: 4 }),
          'monitor.wantedFailed' + JSON.stringify({ count: 1 }),
          'monitor.wantedSkipped' + JSON.stringify({ count: 2 }),
          'monitor.wantedStopped',
        ].join(' · ')
      )
    })

    it('leaves out the parts that are zero', () => {
      const job = { kind: 'check', running: false, done: 3, total: 3 }
      expect(jobText(job, t)).toBe(
        'monitor.wantedFinished' + JSON.stringify({ done: 3 })
      )
    })
  })
})
