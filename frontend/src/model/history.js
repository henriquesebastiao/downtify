// "Jump back in": the albums, playlists and artists played recently.
import { ref } from 'vue'

const STORAGE_KEY = 'downtify-recent-contexts'
const LIMIT = 12

function read() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

const recent = ref(read())

/** `entry`: { type, title, subtitle, route, cover } */
function remember(entry) {
  if (!entry?.type || !entry?.title) return
  const id = `${entry.type}:${entry.title}:${entry.subtitle || ''}`
  const next = [
    { ...entry, id, playedAt: Date.now() },
    ...recent.value.filter((item) => item.id !== id),
  ].slice(0, LIMIT)
  recent.value = next
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // ignore
  }
}

export function useHistory() {
  return { recent, remember }
}
