// Play / queue / delete actions shared by every track list and page.
import { useRouter } from 'vue-router'

import { usePlayer } from '/src/model/player'
import { useLibrary } from '/src/model/library'
import { useHistory } from '/src/model/history'
import { useUi } from '/src/model/ui'
import { saveName } from '/src/lib/paths'
import { useI18n } from '/src/i18n'

export function useTrackActions() {
  const player = usePlayer()
  const library = useLibrary()
  const history = useHistory()
  const ui = useUi()
  const router = useRouter()
  const { t } = useI18n()

  /**
   * Play `tracks` from `index`. `context`: { type, title, subtitle,
   * route, cover } — remembered for "Jump back in".
   */
  function play(tracks, index = 0, context = null, { shuffled = false } = {}) {
    if (!tracks.length) return
    if (shuffled) {
      player.playList(tracks, { context, shuffled: true })
    } else {
      player.setPlaylist(tracks, { startIndex: index, context })
    }
    if (context && context.type !== 'library') history.remember(context)
  }

  function playNext(tracks) {
    player.playNext(tracks)
    ui.toast(t('toast.playingNext', { count: tracks.length }), {
      kind: 'success',
    })
  }

  function enqueue(tracks) {
    player.enqueue(tracks)
    ui.toast(t('toast.addedToQueue', { count: tracks.length }), {
      kind: 'success',
    })
  }

  function saveToDevice(track) {
    const a = document.createElement('a')
    a.href = track.url
    a.download = saveName(track.file)
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  async function downloadZip(tracks) {
    try {
      await library.downloadZip(tracks.map((track) => track.file))
      ui.toast(t('toast.zipStarted', { count: tracks.length }), {
        kind: 'success',
      })
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.zipFailed'), {
        kind: 'error',
      })
    }
  }

  /** Confirm, delete and report; resolves the deleted files. */
  async function remove(tracks) {
    if (!tracks.length) return []
    const ok = await ui.confirm({
      title:
        tracks.length === 1
          ? t('confirm.deleteTrackTitle', { title: tracks[0].title })
          : t('confirm.deleteTracksTitle', { count: tracks.length }),
      body: t('confirm.deleteTracksBody'),
      confirmLabel: t('common.delete'),
      danger: true,
    })
    if (!ok) return []
    try {
      const { deleted, failed } = await library.deleteFiles(
        tracks.map((track) => track.file)
      )
      if (failed) {
        ui.toast(t('toast.deletePartial', { count: failed }), { kind: 'error' })
      } else {
        ui.toast(t('toast.deleted', { count: deleted.length }), {
          kind: 'success',
        })
      }
      return deleted
    } catch {
      ui.toast(t('toast.deleteFailed'), { kind: 'error' })
      return []
    }
  }

  /** Context-menu items for one track inside `list`. */
  function menuFor(
    track,
    { list = [track], index = 0, context = null, hide = [] } = {}
  ) {
    return [
      {
        label: t('actions.play'),
        icon: 'play',
        action: () => play(list, index, context),
      },
      {
        label: t('actions.playNext'),
        icon: 'play-next',
        action: () => playNext([track]),
      },
      {
        label: t('actions.addToQueue'),
        icon: 'queue',
        action: () => enqueue([track]),
      },
      { divider: true },
      {
        label: t('actions.goToAlbum'),
        icon: 'disc',
        hidden: !track.album || hide.includes('album'),
        action: () =>
          router.push({
            name: 'Album',
            query: { artist: track.albumArtist, title: track.album },
          }),
      },
      {
        label: t('actions.goToArtist'),
        icon: 'user',
        hidden: !track.albumArtist || hide.includes('artist'),
        action: () =>
          router.push({ name: 'Artist', query: { name: track.albumArtist } }),
      },
      {
        label: t('library.saveToDevice'),
        icon: 'download',
        action: () => saveToDevice(track),
      },
      { divider: true },
      {
        label: t('actions.delete'),
        icon: 'trash',
        danger: true,
        action: () => remove([track]),
      },
    ]
  }

  return { play, playNext, enqueue, saveToDevice, downloadZip, remove, menuFor }
}
