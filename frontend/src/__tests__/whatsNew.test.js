import { describe, expect, it } from 'vitest'

import { AVAILABLE_LOCALES } from '../i18n'
import notes from '../lib/releaseHighlights.js'
import {
  LAST_VERSION_KEY,
  SEEN_KEY,
  highlightsFor,
  isNewer,
  isRelease,
  markWhatsNewSeen,
  parseVersion,
  releaseUrl,
  seedSeenVersion,
  shouldShowWhatsNew,
} from '../lib/whatsNew.js'

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial))
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
    data,
  }
}

describe('versions', () => {
  it('compares numerically, not as text', () => {
    expect(isNewer('3.10.0', '3.9.0')).toBe(true)
    expect(isNewer('3.9.0', '3.10.0')).toBe(false)
    expect(isNewer('3.12.0', '3.12.0')).toBe(false)
    expect(isNewer('4.0.0', '3.99.99')).toBe(true)
    expect(isNewer('v3.12.1', '3.12.0')).toBe(true)
  })

  it('never calls an unreadable version newer', () => {
    expect(isNewer('', '3.12.0')).toBe(false)
    expect(isNewer('3.12.0', null)).toBe(false)
    expect(parseVersion('dev')).toBeNull()
  })

  it('treats the offline 0.0.0 as no release', () => {
    expect(isRelease('0.0.0')).toBe(false)
    expect(isRelease('3.12.0')).toBe(true)
    expect(isRelease(undefined)).toBe(false)
  })

  it('links to the GitHub release of that version', () => {
    expect(releaseUrl('3.12.0')).toBe(
      'https://github.com/henriquesebastiao/downtify/releases/tag/3.12.0'
    )
  })
})

describe('when to show', () => {
  it('shows nothing on a fresh install, and remembers the version', () => {
    const storage = memoryStorage()
    seedSeenVersion(storage)
    expect(shouldShowWhatsNew(storage, '3.12.0')).toBe(false)
    expect(storage.getItem(SEEN_KEY)).toBe('3.12.0')
  })

  it('shows once after an update, until dismissed', () => {
    const storage = memoryStorage({ [SEEN_KEY]: '3.11.0' })
    expect(shouldShowWhatsNew(storage, '3.12.0')).toBe(true)
    // A reload before dismissing shows it again.
    expect(shouldShowWhatsNew(storage, '3.12.0')).toBe(true)
    markWhatsNewSeen(storage, '3.12.0')
    expect(shouldShowWhatsNew(storage, '3.12.0')).toBe(false)
  })

  it('announces the first update of a browser that ran an older build', () => {
    // Older builds only remembered the last version they ran.
    const storage = memoryStorage({ [LAST_VERSION_KEY]: '3.11.0' })
    seedSeenVersion(storage)
    expect(storage.getItem(SEEN_KEY)).toBe('3.11.0')
    expect(shouldShowWhatsNew(storage, '3.12.0')).toBe(true)
  })

  it('keeps an existing mark when the app reloads on a new version', () => {
    const storage = memoryStorage({
      [SEEN_KEY]: '3.10.0',
      [LAST_VERSION_KEY]: '3.12.0',
    })
    seedSeenVersion(storage)
    expect(storage.getItem(SEEN_KEY)).toBe('3.10.0')
  })

  it('ignores the offline fallback and downgrades', () => {
    expect(
      shouldShowWhatsNew(memoryStorage({ [SEEN_KEY]: '3.12.0' }), '0.0.0')
    ).toBe(false)
    expect(
      shouldShowWhatsNew(memoryStorage({ [SEEN_KEY]: '3.12.0' }), '3.11.0')
    ).toBe(false)
    const storage = memoryStorage({ [LAST_VERSION_KEY]: '0.0.0' })
    seedSeenVersion(storage)
    expect(storage.getItem(SEEN_KEY)).toBeNull()
  })

  it('survives storage that throws', () => {
    const broken = {
      getItem: () => {
        throw new Error('blocked')
      },
      setItem: () => {
        throw new Error('blocked')
      },
    }
    expect(() => seedSeenVersion(broken)).not.toThrow()
    expect(shouldShowWhatsNew(broken, '3.12.0')).toBe(false)
    expect(() => markWhatsNewSeen(broken, '3.12.0')).not.toThrow()
  })
})

describe('highlights', () => {
  const sample = { '1.2.0': { en: ['A'], 'pt-BR': ['B'], de: ['C'] } }

  it('picks the language, else English, else nothing', () => {
    expect(highlightsFor(sample, '1.2.0', 'pt-BR')).toEqual(['B'])
    expect(highlightsFor(sample, '1.2.0', 'de')).toEqual(['C'])
    expect(highlightsFor(sample, '1.2.0', 'ko')).toEqual(['A'])
    expect(highlightsFor(sample, '9.9.9', 'en')).toEqual([])
  })

  const codes = new Set(AVAILABLE_LOCALES.map((l) => l.code))
  for (const [version, entry] of Object.entries(notes)) {
    it(`${version} is a version with English lines in app languages`, () => {
      expect(parseVersion(version)?.join('.')).toBe(version)
      expect(entry.en?.length).toBeGreaterThan(0)
      for (const [code, lines] of Object.entries(entry)) {
        expect(codes.has(code), `unknown language ${code}`).toBe(true)
        expect(lines.length, `${version} ${code}`).toBe(entry.en.length)
        for (const line of lines) expect(line.trim()).not.toBe('')
      }
    })
  }
})
