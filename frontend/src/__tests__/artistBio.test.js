import { describe, expect, it } from 'vitest'
import { artistFacts, isSoloArtist } from '../lib/artistBio'

// A translator that shows which key and values it was given.
const t = (key, params = {}) => `${key}(${JSON.stringify(params)})`

describe('isSoloArtist', () => {
  it('is only an explicit is_group: false', () => {
    expect(isSoloArtist({ is_group: false })).toBe(true)
    expect(isSoloArtist({ is_group: true })).toBe(false)
    // A profile saved before Apple Music's flag was kept: unknown.
    expect(isSoloArtist({ is_group: null })).toBe(false)
    expect(isSoloArtist({})).toBe(false)
    expect(isSoloArtist(null)).toBe(false)
  })
})

describe('artistFacts', () => {
  it('says a group was formed', () => {
    expect(
      artistFacts(
        {
          is_group: true,
          born_or_formed: 'novembro de 1973',
          origin: 'Sydney, Australia',
        },
        t
      )
    ).toBe('artistBio.formed({"year":"novembro de 1973"}) — Sydney, Australia')
  })

  it('says a solo artist was born', () => {
    expect(
      artistFacts(
        {
          is_group: false,
          born_or_formed: '27 de setembro de 1984',
          origin: 'Napanee, Ontario, CA',
        },
        t
      )
    ).toBe(
      'artistBio.born({"date":"27 de setembro de 1984"}) — Napanee, Ontario, CA'
    )
  })

  it('keeps "formed" when nothing says whether it is a group', () => {
    expect(artistFacts({ is_group: null, born_or_formed: '1995' }, t)).toBe(
      'artistBio.formed({"year":"1995"})'
    )
    expect(artistFacts({ born_or_formed: '1995' }, t)).toBe(
      'artistBio.formed({"year":"1995"})'
    )
  })

  it('shows just what is known', () => {
    expect(artistFacts({ is_group: false, origin: 'Napanee' }, t)).toBe(
      'Napanee'
    )
    expect(artistFacts({ is_group: false, born_or_formed: '1984' }, t)).toBe(
      'artistBio.born({"date":"1984"})'
    )
    expect(artistFacts({ is_group: false }, t)).toBe('')
    expect(artistFacts(null, t)).toBe('')
  })
})
