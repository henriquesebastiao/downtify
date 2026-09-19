import { describe, expect, it } from 'vitest'
import { isFirstLike, likedSet, withLike } from '../lib/likes.js'

describe('likedSet', () => {
  it('collects the liked files', () => {
    expect(likedSet(['a.mp3', 'b/c.flac'])).toEqual(
      new Set(['a.mp3', 'b/c.flac'])
    )
  })

  it('drops duplicates and anything that is not a file name', () => {
    expect(likedSet(['a.mp3', 'a.mp3', '', null, 4, {}])).toEqual(
      new Set(['a.mp3'])
    )
  })

  it('survives a missing or malformed list', () => {
    expect(likedSet(undefined).size).toBe(0)
    expect(likedSet(null).size).toBe(0)
    expect(likedSet('a.mp3').size).toBe(0)
  })
})

describe('withLike', () => {
  it('adds and removes a file', () => {
    const before = new Set(['a.mp3'])
    expect(withLike(before, 'b.mp3', true)).toEqual(new Set(['a.mp3', 'b.mp3']))
    expect(withLike(before, 'a.mp3', false).size).toBe(0)
  })

  it('never mutates the set it was given', () => {
    const before = new Set(['a.mp3'])
    withLike(before, 'b.mp3', true)
    withLike(before, 'a.mp3', false)
    expect(before).toEqual(new Set(['a.mp3']))
  })

  it('is idempotent, so a repeated tap or a late echo is harmless', () => {
    const liked = new Set(['a.mp3'])
    expect(withLike(liked, 'a.mp3', true)).toEqual(liked)
    expect(withLike(liked, 'zzz.mp3', false)).toEqual(liked)
  })

  it('undoes one failed tap without touching the others', () => {
    // A tap on b failed while a was liked meanwhile: only b reverts.
    const now = new Set(['a.mp3', 'b.mp3'])
    expect(withLike(now, 'b.mp3', false)).toEqual(new Set(['a.mp3']))
  })
})

describe('isFirstLike', () => {
  it('is the like made while nothing was liked', () => {
    expect(isFirstLike(new Set(), true)).toBe(true)
  })

  it('is not a like on top of others', () => {
    expect(isFirstLike(new Set(['a.mp3']), true)).toBe(false)
  })

  it('is never an unlike', () => {
    expect(isFirstLike(new Set(), false)).toBe(false)
    expect(isFirstLike(new Set(['a.mp3']), false)).toBe(false)
  })
})
