import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import {
  PREVIEW_RING_LENGTH,
  PREVIEW_SECONDS,
  previewRatio,
  previewUrl,
  ringOffset,
} from '../lib/preview.js'

const CLIP = 'https://p.scdn.co/mp3-preview/b5ee275ca337899f762b1c1883c11e24'

describe('previewUrl', () => {
  it('is the https clip of a song', () => {
    expect(previewUrl({ preview_url: CLIP })).toBe(CLIP)
  })

  it('is empty when the song has none, or not an https link', () => {
    expect(previewUrl({})).toBe('')
    expect(previewUrl(null)).toBe('')
    expect(previewUrl({ preview_url: '' })).toBe('')
    expect(previewUrl({ preview_url: 42 })).toBe('')
    expect(previewUrl({ preview_url: 'http://p.scdn.co/x' })).toBe('')
    expect(previewUrl({ preview_url: 'javascript:alert(1)' })).toBe('')
  })
})

describe('previewRatio', () => {
  it('is how far into the clip, from 0 to 1', () => {
    expect(previewRatio(0, 29.7)).toBe(0)
    expect(previewRatio(15, 30)).toBe(0.5)
    expect(previewRatio(30, 30)).toBe(1)
  })

  it('never leaves 0..1', () => {
    expect(previewRatio(-3, 30)).toBe(0)
    expect(previewRatio(45, 30)).toBe(1)
    expect(previewRatio(NaN, 30)).toBe(0)
  })

  it('counts on a 30 s clip until the real length is known', () => {
    expect(previewRatio(15, NaN)).toBe(15 / PREVIEW_SECONDS)
    expect(previewRatio(15, 0)).toBe(15 / PREVIEW_SECONDS)
    expect(previewRatio(15, Infinity)).toBe(15 / PREVIEW_SECONDS)
  })
})

describe('ringOffset', () => {
  it('draws none of the ring at the start and all of it at the end', () => {
    expect(ringOffset(0)).toBe(PREVIEW_RING_LENGTH)
    expect(ringOffset(1)).toBe(0)
    expect(ringOffset(0.25)).toBeCloseTo(PREVIEW_RING_LENGTH * 0.75)
  })
})

// The clip player, driven through a fake <audio> element.
class FakeAudio {
  static all = []

  constructor() {
    this.src = ''
    this.currentTime = 0
    this.duration = NaN
    this.volume = 1
    this.muted = false
    this.paused = true
    this.listeners = {}
    FakeAudio.all.push(this)
  }
  addEventListener(name, fn) {
    ;(this.listeners[name] ||= []).push(fn)
  }
  emit(name) {
    for (const fn of this.listeners[name] || []) fn()
  }
  play() {
    this.paused = false
    this.emit('play')
    return Promise.resolve()
  }
  pause() {
    this.paused = true
    this.emit('pause')
  }
  removeAttribute() {
    this.src = ''
  }
  load() {}
}

const SONG = { song_id: 'a'.repeat(22), name: 'One', preview_url: CLIP }
const OTHER = {
  song_id: 'b'.repeat(22),
  name: 'Two',
  preview_url: `${CLIP}2`,
}

describe('usePreview', () => {
  let preview
  let player

  // The clip's <audio>: made on first use, so after the player's own.
  const clip = () => FakeAudio.all.at(-1)

  beforeEach(async () => {
    vi.resetModules()
    FakeAudio.all = []
    globalThis.localStorage = { getItem: () => null, setItem: () => {} }
    globalThis.Audio = FakeAudio
    ;({ usePlayer: player } = await import('../model/player.js'))
    player = player()
    ;({ usePreview: preview } = await import('../model/preview.js'))
    preview = preview()
  })

  afterEach(() => {
    delete globalThis.Audio
  })

  it('starts the clip of a song and knows which one plays', () => {
    preview.toggle(SONG)
    expect(preview.activeId.value).toBe(SONG.song_id)
    expect(preview.isPlaying.value).toBe(true)
    expect(clip().src).toBe(CLIP)
  })

  it('plays at the level the player is set to', () => {
    player.setVolume(0.4)
    preview.toggle(SONG)
    expect(clip().volume).toBe(0.4)
    expect(clip().muted).toBe(false)
  })

  it('pauses on the second press and resumes on the third', () => {
    preview.toggle(SONG)
    preview.toggle(SONG)
    expect(preview.activeId.value).toBe(SONG.song_id)
    expect(preview.isPlaying.value).toBe(false)
    expect(clip().paused).toBe(true)
    preview.toggle(SONG)
    expect(preview.isPlaying.value).toBe(true)
    expect(clip().paused).toBe(false)
  })

  it('plays one clip at a time: another song takes over', () => {
    preview.toggle(SONG)
    preview.toggle(OTHER)
    expect(preview.activeId.value).toBe(OTHER.song_id)
    expect(preview.progress.value).toBe(0)
    expect(clip().src).toBe(OTHER.preview_url)
  })

  it('ignores a song with no clip or no id', () => {
    preview.toggle({ song_id: SONG.song_id, name: 'x' })
    preview.toggle({ preview_url: CLIP })
    preview.toggle({ song_id: SONG.song_id, preview_url: 'http://p.scdn.co/x' })
    preview.toggle(null)
    expect(preview.activeId.value).toBe('')
    expect(FakeAudio.all).toHaveLength(0)
  })

  it('follows the clip: loading until it plays, then how far it is', () => {
    preview.toggle(SONG)
    expect(preview.isLoading.value).toBe(true)
    clip().emit('playing')
    expect(preview.isLoading.value).toBe(false)
    clip().duration = 30
    clip().currentTime = 7.5
    clip().emit('timeupdate')
    expect(preview.progress.value).toBe(0.25)
  })

  it('goes back to idle when the clip ends', () => {
    preview.toggle(SONG)
    clip().emit('ended')
    expect(preview.activeId.value).toBe('')
    expect(preview.isPlaying.value).toBe(false)
    expect(preview.progress.value).toBe(0)
  })

  it('goes back to idle when the clip cannot be played', () => {
    preview.toggle(SONG)
    clip().emit('error')
    expect(preview.activeId.value).toBe('')
    expect(preview.isLoading.value).toBe(false)
  })

  it('goes back to idle when the browser refuses to start it', async () => {
    const original = FakeAudio.prototype.play
    FakeAudio.prototype.play = function play() {
      original.call(this)
      return Promise.reject(new Error('NotAllowedError'))
    }
    try {
      preview.toggle(SONG)
      await Promise.resolve()
      await Promise.resolve()
    } finally {
      FakeAudio.prototype.play = original
    }
    expect(preview.activeId.value).toBe('')
  })

  it('does not end a newer clip when the older start is refused late', async () => {
    let refuse
    const original = FakeAudio.prototype.play
    FakeAudio.prototype.play = function play() {
      original.call(this)
      return new Promise((_, reject) => {
        refuse = reject
      })
    }
    preview.toggle(SONG)
    const refuseFirst = refuse
    FakeAudio.prototype.play = original
    preview.toggle(OTHER)
    refuseFirst(new Error('AbortError'))
    await Promise.resolve()
    await Promise.resolve()
    expect(preview.activeId.value).toBe(OTHER.song_id)
    expect(preview.isPlaying.value).toBe(true)
  })

  it('pauses the built-in player when a clip starts', () => {
    player.setPlaylist(['A - One.mp3'], { startIndex: 0 })
    expect(player.isPlaying.value).toBe(true)
    preview.toggle(SONG)
    expect(player.isPlaying.value).toBe(false)
    expect(preview.isPlaying.value).toBe(true)
  })

  it('ends the clip when the built-in player starts', async () => {
    player.setPlaylist(['A - One.mp3'], { startIndex: 0 })
    player.pause()
    preview.toggle(SONG)
    expect(preview.isPlaying.value).toBe(true)
    player.play()
    await nextTick()
    expect(preview.activeId.value).toBe('')
    expect(preview.isPlaying.value).toBe(false)
    expect(player.isPlaying.value).toBe(true)
  })

  it('stops only the clip of the row that asked', () => {
    preview.toggle(SONG)
    preview.stopFor(OTHER.song_id)
    expect(preview.activeId.value).toBe(SONG.song_id)
    preview.stopFor(SONG.song_id)
    expect(preview.activeId.value).toBe('')
  })
})
