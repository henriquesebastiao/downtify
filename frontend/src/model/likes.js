// Liked songs: the heart on a library track. The likes live on the server
// (so a heart tapped on a phone is there on the desktop), and while there
// is at least one, the server also writes them out as a playlist.
import { computed, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'

import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { isFirstLike, likedSet, withLike } from '/src/lib/likes'
import { useI18n } from '/src/i18n'

const liked = shallowRef(new Set())
const loaded = ref(false)
// The name the playlist has on disk, for links to it.
const playlistName = ref('')
// Taps sent but not yet answered. While there are any, a refresh from the
// server could still predate them and would undo a heart that is about to
// be confirmed.
let pending = 0
let stale = false

async function load() {
  try {
    const res = await API.getLikes()
    liked.value = likedSet(res.data?.files)
    playlistName.value = String(res.data?.playlist || '')
    loaded.value = true
  } catch {
    // Keep what is shown; the next change or reconnect tries again.
  }
}

function refresh() {
  if (pending > 0) {
    stale = true
    return
  }
  stale = false
  return load()
}

function settled() {
  pending -= 1
  if (pending === 0 && stale) refresh()
}

// Another tab or device changed the likes (or a deleted song was
// unliked): follow it, and pick up the playlist that came or went.
API.onMessage((data) => {
  if (data?.type !== 'likes') return
  refresh()
  useLibrary().refreshSoon(800)
})

export function useLikes() {
  const library = useLibrary()
  const ui = useUi()
  const router = useRouter()
  const { t } = useI18n()

  const count = computed(() => liked.value.size)

  function isLiked(file) {
    return liked.value.has(file)
  }

  /** Like or unlike `file`, showing it at once and undoing it if it fails. */
  async function set(file, on) {
    if (!file || isLiked(file) === on) return true
    const first = isFirstLike(liked.value, on)
    liked.value = withLike(liked.value, file, on)
    pending += 1
    try {
      await API.setLike(file, on)
      // The playlist appears with the first like and follows every change.
      library.refreshSoon(1200)
      if (first) announceCreated()
      return true
    } catch (err) {
      // Undo only this tap: another one may have landed since.
      liked.value = withLike(liked.value, file, !on)
      ui.toast(err?.response?.data?.detail || t('likes.failed'), {
        kind: 'error',
      })
      return false
    } finally {
      settled()
    }
  }

  function toggle(file) {
    return set(file, !isLiked(file))
  }

  function announceCreated() {
    ui.toast(t('likes.created'), {
      kind: 'success',
      action: playlistName.value
        ? {
            label: t('likes.open'),
            run: () =>
              router.push({
                name: 'Playlist',
                query: { name: playlistName.value },
              }),
          }
        : null,
    })
  }

  /** Unlike everything. The songs stay in the library. */
  async function clear() {
    pending += 1
    try {
      await API.clearLikes()
      liked.value = new Set()
      library.refreshSoon(300)
      return true
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('likes.failed'), {
        kind: 'error',
      })
      return false
    } finally {
      settled()
    }
  }

  return { liked, loaded, count, isLiked, set, toggle, clear, load }
}

// The hearts should be filled the first time a track list shows.
load()
