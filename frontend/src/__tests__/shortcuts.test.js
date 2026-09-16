import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { createShortcutHandler } from '../components/shell/shortcuts'

function setup({ modal = false } = {}) {
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
