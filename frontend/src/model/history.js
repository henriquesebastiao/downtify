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

function persist(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // ignore
  }
}

function entryId(entry) {
  return `${entry.type}:${entry.title}:${entry.subtitle || ''}`
}

function playlistNameOf(entry) {
  return String(entry?.route?.query?.name || '')
}

const recent = ref(read())

/** `entry`: { type, title, subtitle, route, cover } */
function remember(entry) {
  if (!entry?.type || !entry?.title) return
  const id = entryId(entry)
  const next = [
    { ...entry, id, playedAt: Date.now() },
    ...recent.value.filter((item) => item.id !== id),
  ].slice(0, LIMIT)
  recent.value = next
  persist(next)
}

function retitlePlaylist(previous, name) {
  const from = String(previous || '')
  const to = String(name || '')
  if (!from || !to || from === to) return
  const next = []
  const seen = new Set()
  for (const entry of recent.value) {
    let item = entry
    if (entry.type === 'playlist') {
      const listed = playlistNameOf(entry)
      if (listed === from || entry.title === from) {
        const route = entry.route
          ? {
              ...entry.route,
              query: { ...(entry.route.query || {}), name: to },
            }
          : { name: 'Playlist', query: { name: to } }
        item = { ...entry, title: to, route }
        item.id = entryId(item)
      }
    }
    if (seen.has(item.id)) continue
    seen.add(item.id)
    next.push(item)
  }
  recent.value = next
  persist(next)
}

export function useHistory() {
  return { recent, remember, retitlePlaylist }
}
