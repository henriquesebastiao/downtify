// Actions for downloaded playlists (library + Spotify download tracking).
import { useRouter } from 'vue-router'

import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import { syncQueueFromServer } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

export function usePlaylistActions() {
  const library = useLibrary()
  const tracks = useTrackActions()
  const ui = useUi()
  const router = useRouter()
  const { t } = useI18n()

  function contextFor(playlist) {
    return {
      type: 'playlist',
      title: playlist.name,
      cover: playlist.covers[0] || '',
      route: { name: 'Playlist', query: { name: playlist.name } },
    }
  }

  function play(playlist, options = {}) {
    tracks.play(playlist.tracks, 0, contextFor(playlist), options)
  }

  async function downloadMissing(playlist) {
    const batch = playlist.batch
    if (!batch) return
    try {
      const res = await API.downloadMissingPlaylistTracks({
        spotify_playlist_id: batch.spotify_playlist_id,
        playlist_url: batch.playlist_url,
      })
      const count = res.data?.count || 0
      if (count) {
        ui.toast(t('toast.queuedMissing', { count }), {
          kind: 'success',
          action: {
            label: t('nav.queue'),
            run: () => router.push({ name: 'Queue' }),
          },
        })
        syncQueueFromServer().catch(() => {})
      } else {
        ui.toast(t('toast.playlistComplete'), { kind: 'success' })
      }
      library.refreshSoon(500)
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
    }
  }

  async function watch(playlist) {
    const url = playlist.batch?.playlist_url
    if (!url) return
    try {
      await monitorAPI.addMonitoredPlaylist(url, 360)
      ui.toast(t('toast.watching', { name: playlist.name }), {
        kind: 'success',
        action: {
          label: t('nav.monitor'),
          run: () =>
            router.push({ name: 'Monitor', params: { tab: 'playlists' } }),
        },
      })
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
    }
  }

  async function remove(playlist) {
    const ok = await ui.confirm({
      title: t('confirm.deletePlaylistTitle', { name: playlist.name }),
      body: t('confirm.deletePlaylistBody'),
      confirmLabel: t('common.delete'),
      danger: true,
    })
    if (!ok) return false
    try {
      const result = await library.deletePlaylist(playlist)
      ui.toast(
        t('toast.playlistDeleted', {
          name: playlist.name,
          count: result?.deleted_count ?? 0,
        }),
        { kind: 'success' }
      )
      return true
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
      return false
    }
  }

  function menuFor(playlist, { hide = [] } = {}) {
    const batch = playlist.batch
    const empty = !playlist.tracks.length
    return [
      {
        label: t('actions.play'),
        icon: 'play',
        hidden: empty,
        action: () => play(playlist),
      },
      {
        label: t('actions.shuffle'),
        icon: 'shuffle',
        hidden: empty,
        action: () => play(playlist, { shuffled: true }),
      },
      {
        label: t('actions.addToQueue'),
        icon: 'queue',
        hidden: empty,
        action: () => tracks.enqueue(playlist.tracks),
      },
      { divider: true },
      {
        label: t('playlists.downloadMissing', {
          count: batch?.missing_count || 0,
        }),
        icon: 'download',
        hidden: !batch?.missing_count,
        action: () => downloadMissing(playlist),
      },
      {
        label: t('playlists.watch'),
        icon: 'radar',
        hidden: !batch?.playlist_url || hide.includes('watch'),
        action: () => watch(playlist),
      },
      {
        label: t('playlists.openSource'),
        icon: 'arrow-up-right',
        hidden: !batch?.playlist_url,
        action: () => window.open(batch.playlist_url, '_blank', 'noopener'),
      },
      {
        label: t('library.downloadZip'),
        icon: 'zip',
        hidden: empty,
        action: () => tracks.downloadZip(playlist.tracks),
      },
      { divider: true },
      {
        label: t('playlists.delete'),
        icon: 'trash',
        danger: true,
        action: () => remove(playlist),
      },
    ]
  }

  return { contextFor, play, downloadMissing, watch, remove, menuFor }
}
