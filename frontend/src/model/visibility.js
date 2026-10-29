// Hiding songs, albums and artists from users, and showing them again
// (admins; see downtify/library_visibility.py). Menus and selections call
// these; the Library follows without a reload.
import { useAuth } from '/src/model/auth'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import API from '/src/model/api'
import {
  albumItem,
  applyVisibility,
  artistItem,
  trackItem,
  visibilityAction,
} from '/src/lib/visibility'
import { useI18n } from '/src/i18n'

export function useVisibility() {
  const auth = useAuth()
  const library = useLibrary()
  const ui = useUi()
  const { t } = useI18n()

  /** Hide (`action: 'hide'`) or show `items`; resolves whether it worked. */
  async function change(action, items) {
    if (!items.length) return false
    try {
      await API.updateLibraryVisibility(action, items)
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
      return false
    }
    library.tracks.value = applyVisibility(library.tracks.value, action, items)
    ui.toast(
      t(action === 'hide' ? 'visibility.hidden' : 'visibility.shown', {
        count: items.length,
      }),
      { kind: 'success' }
    )
    // Album and artist grids come from the server's own index.
    void library.load({ force: true })
    return true
  }

  // One menu entry for a track, album or artist: hide it from users, or
  // show it again. Nothing for non-admins, or when a wider rule hides it.
  function menuItem(source, own, toItem) {
    if (!auth.isAdmin.value) return []
    const action = visibilityAction(source.hiddenBy, own)
    if (!action) return []
    return [
      {
        label: t(action === 'hide' ? 'visibility.hide' : 'visibility.show'),
        icon: action === 'hide' ? 'eye-off' : 'eye',
        action: () => change(action, [toItem(source)]),
      },
    ]
  }

  return {
    change,
    trackMenu: (track) => menuItem(track, 'track', trackItem),
    albumMenu: (album) => menuItem(album, 'album', albumItem),
    artistMenu: (artist) => menuItem(artist, 'artist', artistItem),
  }
}
