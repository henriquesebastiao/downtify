import { describe, expect, it } from 'vitest'
import {
  NAMES_SHOWN,
  TYPES,
  filterWanted,
  jobText,
  listedReleases,
  namesText,
  summary,
  summaryText,
  uncheckedNames,
} from '../lib/wantedReleases.js'

const release = (name, section = 'album', extra = {}) => ({
  id: name,
  name,
  section,
  state: 'missing',
  checked: true,
  ...extra,
})

const artist = (name, releases, unchecked = 0, id = name) => ({
  watch: { id, name },
  releases,
  missing: { tracks: 0, releases: releases.length, unread: unchecked },
  unchecked,
  checking: false,
})

const artists = [
  artist('Beyoncé', [release('Lemonade'), release('Renaissance')]),
  artist('Drake', [release('Views'), release('Scary Hours', 'ep')]),
  artist('Unread Act', [release('Unread LP', 'album', { checked: false })], 1),
  artist(
    'Unread With Known',
    [
      release('Known Single', 'single'),
      release('Unread EP', 'ep', { checked: false }),
    ],
    1
  ),
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

  it('drops an artist with no release left under a type or search', () => {
    const out = filterWanted(artists, { type: 'ep' }).map((a) => a.watch.name)
    expect(out).toEqual(['Drake', 'Unread With Known'])
    expect(filterWanted(artists, { type: 'mixtape' })).toEqual([])
    expect(filterWanted(artists, { query: 'zzz' })).toEqual([])
    expect(
      filterWanted(artists, { query: 'unread' }).map((a) => a.watch.name)
    ).toEqual(['Unread Act', 'Unread With Known'])
  })

  it('combines query and type', () => {
    const out = filterWanted(artists, { query: 'drake', type: 'album' })
    const drake = out.find((a) => a.watch.name === 'Drake')
    expect(drake.releases.map((r) => r.name)).toEqual(['Views'])
  })

  it('summarises the totals', () => {
    expect(
      summary({
        tracks: 12,
        releases: 4,
        artists: 2,
        unchecked: 1,
        unchecked_releases: 3,
      })
    ).toEqual({ tracks: 12, releases: 4, unchecked: 1, uncheckedReleases: 3 })
    expect(summary(null)).toEqual({
      tracks: 0,
      releases: 0,
      unchecked: 0,
      uncheckedReleases: 0,
    })
  })

  it('words the summary through pluralised pieces', () => {
    expect(summaryText({ tracks: 12, releases: 4 }, t)).toBe(
      'monitor.wantedSummary' +
        JSON.stringify({
          songs: 'monitor.wantedSongs{"count":12}',
          releases: 'monitor.wantedReleases{"count":4}',
        })
    )
  })

  it('counts the releases listed, read or not', () => {
    expect(listedReleases(artists)).toBe(7)
    expect(listedReleases([])).toBe(0)
  })

  it('names the artists with releases not checked yet', () => {
    expect(uncheckedNames(artists)).toEqual(['Unread Act', 'Unread With Known'])
    expect(uncheckedNames([])).toEqual([])
  })

  describe('namesText', () => {
    it('lists a few names in full', () => {
      expect(namesText(['Ace', 'Bee'], t)).toBe('Ace, Bee')
      expect(namesText([], t)).toBe('')
      const few = Array.from({ length: NAMES_SHOWN }, (_, i) => `A${i}`)
      expect(namesText(few, t)).toBe(few.join(', '))
    })

    it('caps a long list and counts the rest', () => {
      const names = Array.from({ length: 87 }, (_, i) => `A${i}`)
      expect(namesText(names, t)).toBe(
        `A0, A1, A2 monitor.wantedMore${JSON.stringify({ count: 84 })}`
      )
    })
  })

  describe('jobText', () => {
    it('is empty without a job', () => {
      expect(jobText(null, t)).toBe('')
    })

    it('reads a running check, counting the artist being worked on', () => {
      const job = { kind: 'check', running: true, done: 2, total: 5 }
      expect(jobText({ ...job, current: 'Drake' }, t)).toBe(
        'monitor.wantedChecking' +
          JSON.stringify({ done: 3, total: 5, name: 'Drake' })
      )
    })

    it('starts at 1 of N, never past the total', () => {
      const first = { kind: 'check', running: true, done: 0, total: 87 }
      expect(jobText({ ...first, current: 'Ace' }, t)).toBe(
        'monitor.wantedChecking' +
          JSON.stringify({ done: 1, total: 87, name: 'Ace' })
      )
      expect(jobText({ ...first, done: 87, current: 'Zed' }, t)).toBe(
        'monitor.wantedChecking' +
          JSON.stringify({ done: 87, total: 87, name: 'Zed' })
      )
      // Between two artists nothing is current.
      expect(jobText({ ...first, done: 4, current: '' }, t)).toBe(
        'monitor.wantedChecking' +
          JSON.stringify({ done: 4, total: 87, name: '' })
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
          JSON.stringify({ done: 1, total: 3, name: 'Beyoncé' })
      )
    })

    it('says a Stop was heard', () => {
      const download = {
        kind: 'download',
        running: true,
        stopping: true,
        done: 1,
        total: 3,
        current: 'Drake',
      }
      expect(jobText(download, t)).toBe(
        'monitor.wantedStoppingDownload' + JSON.stringify({ name: 'Drake' })
      )
      expect(jobText({ ...download, current: '' }, t)).toBe(
        'monitor.wantedStoppingCheck'
      )
      expect(jobText({ ...download, kind: 'check' }, t)).toBe(
        'monitor.wantedStoppingCheck'
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
          'monitor.wantedFinished' + JSON.stringify({ count: 4 }),
          'monitor.wantedFailed' + JSON.stringify({ count: 1 }),
          'monitor.wantedSkipped' + JSON.stringify({ count: 2 }),
          'monitor.wantedStopped',
        ].join(' · ')
      )
    })

    it('leaves out the parts that are zero', () => {
      const job = { kind: 'check', running: false, done: 3, total: 3 }
      expect(jobText(job, t)).toBe(
        'monitor.wantedFinished' + JSON.stringify({ count: 3 })
      )
    })
  })
})
