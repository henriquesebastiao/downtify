import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import {
  SHORTCUTS,
  createShortcutHandler,
  visibleShortcuts,
} from '../components/shell/shortcuts'

// `lyrics` is left out to exercise the default (lyrics shown).
function setup({ modal = false, lyrics } = {}) {
  const player = {
    toggle: vi.fn(),
    next: vi.fn(),
    prev: vi.fn(),
    seekBy: vi.fn(),
    setVolume: vi.fn(),
    toggleMute: vi.fn(),
    toggleShuffle: vi.fn(),
    cycleRepeat: vi.fn(),
    currentTrack: ref({ file: 'a.mp3' }),
    volume: ref(0.5),
  }
  const opts = {
    player,
    nowPlaying: { open: vi.fn(), close: vi.fn() },
    focusSearch: vi.fn(),
    openHelp: vi.fn(),
    goTo: vi.fn(),
    hasModal: () => modal,
    closeModal: vi.fn(() => true),
    ...(lyrics === undefined ? {} : { lyricsEnabled: () => lyrics }),
  }
  return { opts, player, handle: createShortcutHandler(opts) }
}

function key(k, extra = {}) {
  return {
    key: k,
    target: { tagName: 'BODY' },
    preventDefault: vi.fn(),
    ...extra,
  }
}

describe('keyboard shortcuts', () => {
  it('toggles playback with space', () => {
    const { handle, player } = setup()
    handle(key(' '))
    expect(player.toggle).toHaveBeenCalledOnce()
  })

  it('ignores keys typed into a field', () => {
    const { handle, player } = setup()
    handle(key(' ', { target: { tagName: 'INPUT' } }))
    expect(player.toggle).not.toHaveBeenCalled()
  })

  it('focuses search with Ctrl+K even while typing', () => {
    const { handle, opts } = setup()
    handle(key('k', { ctrlKey: true, target: { tagName: 'INPUT' } }))
    expect(opts.focusSearch).toHaveBeenCalledOnce()
  })

  it('navigates with g then a letter', () => {
    const { handle, opts } = setup()
    handle(key('g'))
    handle(key('l'))
    expect(opts.goTo).toHaveBeenCalledWith('Library')
  })

  it('opens the lyrics, queue and equalizer panels', () => {
    const { handle, opts } = setup()
    handle(key('l'))
    handle(key('q'))
    handle(key('E'))
    expect(opts.nowPlaying.open.mock.calls).toEqual([
      ['lyrics'],
      ['queue'],
      ['equalizer'],
    ])
  })

  it('leaves the lyrics shortcut alone once lyrics are hidden', () => {
    const { handle, opts } = setup({ lyrics: false })
    handle(key('l'))
    expect(opts.nowPlaying.open).not.toHaveBeenCalled()
    // The other panels are unaffected.
    handle(key('q'))
    handle(key('e'))
    expect(opts.nowPlaying.open.mock.calls).toEqual([['queue'], ['equalizer']])
  })

  it('opens the lyrics when they are shown', () => {
    const { handle, opts } = setup({ lyrics: true })
    handle(key('l'))
    expect(opts.nowPlaying.open).toHaveBeenCalledWith('lyrics')
  })

  it('does not open panels when nothing is playing', () => {
    const { handle, opts, player } = setup()
    player.currentTrack.value = null
    handle(key('e'))
    expect(opts.nowPlaying.open).not.toHaveBeenCalled()
  })

  it('closes now playing with Escape', () => {
    const { handle, opts } = setup()
    handle(key('Escape'))
    expect(opts.nowPlaying.close).toHaveBeenCalledOnce()
  })

  it('lets an open modal swallow shortcuts and closes it on Escape', () => {
    const { handle, opts, player } = setup({ modal: true })
    handle(key(' '))
    handle(key('k', { ctrlKey: true }))
    expect(player.toggle).not.toHaveBeenCalled()
    expect(opts.focusSearch).not.toHaveBeenCalled()
    handle(key('Escape'))
    expect(opts.closeModal).toHaveBeenCalledOnce()
    expect(opts.nowPlaying.close).not.toHaveBeenCalled()
  })
})

describe('visibleShortcuts', () => {
  const labels = (list) => list.map((item) => item.label)

  it('lists everything while lyrics are shown', () => {
    expect(visibleShortcuts({ lyrics: true })).toEqual(SHORTCUTS)
    expect(visibleShortcuts()).toEqual(SHORTCUTS)
  })

  it('drops only the lyrics shortcut when they are hidden', () => {
    const shown = visibleShortcuts({ lyrics: false })
    expect(labels(shown)).not.toContain('shortcuts.lyrics')
    expect(shown).toHaveLength(SHORTCUTS.length - 1)
    expect(labels(shown)).toContain('shortcuts.queue')
  })
})
