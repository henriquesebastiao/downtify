// Global keyboard shortcuts (ignored while typing in a field).
import { onBeforeUnmount, onMounted } from 'vue'

export const SHORTCUTS = [
  { keys: ['Space'], label: 'shortcuts.playPause' },
  { keys: ['→', '←'], label: 'shortcuts.seek' },
  { keys: ['Shift', '→'], label: 'shortcuts.next' },
  { keys: ['Shift', '←'], label: 'shortcuts.previous' },
  { keys: ['↑', '↓'], label: 'shortcuts.volume' },
  { keys: ['M'], label: 'shortcuts.mute' },
  { keys: ['S'], label: 'shortcuts.shuffle' },
  { keys: ['R'], label: 'shortcuts.repeat' },
  { keys: ['L'], label: 'shortcuts.lyrics' },
  { keys: ['Q'], label: 'shortcuts.queue' },
  { keys: ['Ctrl', 'K'], label: 'shortcuts.search' },
  { keys: ['G', 'L'], label: 'shortcuts.goLibrary' },
  { keys: ['G', 'D'], label: 'shortcuts.goQueue' },
  { keys: ['Esc'], label: 'shortcuts.close' },
  { keys: ['?'], label: 'shortcuts.help' },
]

function isTyping(event) {
  const el = event.target
  if (!el) return false
  const tag = el.tagName
  return (
    el.isContentEditable ||
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    tag === 'SELECT'
  )
}

/** Builds the window `keydown` handler (separate from the component
 * lifecycle so it can be tested). */
export function createShortcutHandler({
  player,
  nowPlaying,
  focusSearch,
  openHelp,
  goTo,
  closeModal = () => false,
  hasModal = () => false,
}) {
  let pendingG = 0

  function onKeydown(event) {
    if (hasModal()) {
      if (event.key === 'Escape' && closeModal()) event.preventDefault()
      return
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      focusSearch()
      return
    }
    if (isTyping(event) || event.altKey || event.ctrlKey || event.metaKey) {
      return
    }
    const key = event.key
    if (pendingG && Date.now() - pendingG < 1200) {
      pendingG = 0
      const target = {
        l: 'Library',
        d: 'Queue',
        h: 'Home',
        m: 'Monitor',
        s: 'Settings',
      }[key.toLowerCase()]
      if (target) {
        event.preventDefault()
        goTo(target)
        return
      }
    }
    switch (key) {
      case ' ':
        if (event.target?.tagName === 'BUTTON') return
        event.preventDefault()
        player.toggle()
        break
      case 'ArrowRight':
        event.preventDefault()
        if (event.shiftKey) player.next()
        else player.seekBy(5)
        break
      case 'ArrowLeft':
        event.preventDefault()
        if (event.shiftKey) player.prev()
        else player.seekBy(-5)
        break
      case 'ArrowUp':
        if (!player.currentTrack.value) return
        event.preventDefault()
        player.setVolume(player.volume.value + 0.05)
        break
      case 'ArrowDown':
        if (!player.currentTrack.value) return
        event.preventDefault()
        player.setVolume(player.volume.value - 0.05)
        break
      default:
        handleLetter(event)
    }
  }

  function handleLetter(event) {
    switch (event.key.toLowerCase()) {
      case 'm':
        player.toggleMute()
        break
      case 's':
        player.toggleShuffle()
        break
      case 'r':
        player.cycleRepeat()
        break
      case 'l':
        if (player.currentTrack.value) nowPlaying.open('lyrics')
        break
      case 'q':
        if (player.currentTrack.value) nowPlaying.open('queue')
        break
      case '/':
        event.preventDefault()
        focusSearch()
        break
      case '?':
        openHelp()
        break
      case 'g':
        pendingG = Date.now()
        break
      case 'escape':
        nowPlaying.close()
        break
      default:
    }
  }

  return onKeydown
}

export function useShortcuts(options) {
  const onKeydown = createShortcutHandler(options)
  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
}
