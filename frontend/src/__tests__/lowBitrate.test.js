import { describe, expect, it } from 'vitest'
import {
  anyWorking,
  canReplace,
  canSearch,
  choiceFor,
  errorKey,
  qualityLabel,
  replaceItems,
  replacementPhase,
  sourceKey,
} from '/src/lib/lowBitrate'

const t = (key, params = {}) => `${key}:${JSON.stringify(params)}`

const found = (file, ids, extra = {}) => ({
  file,
  search: {
    state: 'done',
    candidates: ids.map((id) => ({ id, bitrate: 320, format: 'mp3' })),
  },
  replacement: null,
  ...extra,
})

describe('low-bitrate report', () => {
  it('picks the first (best) candidate unless another was chosen', () => {
    const track = found('a.mp3', ['x', 'y'])
    expect(choiceFor(track, {})).toBe('x')
    expect(choiceFor(track, { 'a.mp3': 'y' })).toBe('y')
    // A choice the latest search no longer has falls back to the best.
    expect(choiceFor(track, { 'a.mp3': 'gone' })).toBe('x')
    expect(choiceFor({ file: 'b.mp3', search: null }, {})).toBe('')
  })

  it('replaces only selected tracks that have a copy and are idle', () => {
    const tracks = [
      found('a.mp3', ['x']),
      found('b.mp3', []),
      found('c.mp3', ['z'], { replacement: { state: 'downloading' } }),
      found('d.mp3', ['w']),
    ]
    const items = replaceItems(tracks, ['a.mp3', 'b.mp3', 'c.mp3'], {})
    expect(items).toEqual([{ file: 'a.mp3', candidate: 'x' }])
  })

  it('tells the phases of a replacement apart', () => {
    expect(replacementPhase(null)).toBe('')
    expect(replacementPhase({ state: 'queued' })).toBe('working')
    expect(replacementPhase({ state: 'replacing' })).toBe('working')
    expect(replacementPhase({ state: 'done' })).toBe('done')
    expect(replacementPhase({ state: 'error' })).toBe('error')
  })

  it('does not search a file twice at once', () => {
    expect(canSearch({ search: { state: 'searching' } })).toBe(false)
    expect(canSearch({ replacement: { state: 'queued' } })).toBe(false)
    expect(canSearch({ search: { state: 'done' } })).toBe(true)
    expect(canReplace({ search: { state: 'searching' } })).toBe(false)
  })

  it('polls only while something works', () => {
    expect(anyWorking({ tracks: [found('a.mp3', ['x'])] })).toBe(false)
    expect(anyWorking({ tracks: [{ search: { state: 'queued' } }] })).toBe(true)
  })

  it('labels quality, sources and errors', () => {
    expect(qualityLabel({ bitrate: 320, format: 'mp3' }, t)).toBe(
      'lowBitrate.quality:{"kbps":320,"format":"MP3"}'
    )
    expect(qualityLabel({ bitrate: 245, vbr: true, format: 'mp3' }, t)).toBe(
      'lowBitrate.qualityVbr:{"kbps":245,"format":"MP3"}'
    )
    expect(qualityLabel({ bitrate: 0, format: 'ogg' }, t)).toBe(
      'lowBitrate.noBitrate:{"format":"OGG"}'
    )
    expect(sourceKey('youtube')).toBe('lowBitrate.sources.youtube')
    expect(sourceKey('')).toBe('')
    expect(errorKey('not_better')).toBe('lowBitrate.errors.not_better')
    expect(errorKey('weird')).toBe('lowBitrate.errors.failed')
  })
})
