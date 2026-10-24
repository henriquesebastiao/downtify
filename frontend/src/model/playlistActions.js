// Actions for downloaded playlists (library + Spotify download tracking)
// and for playlists the user creates in the Library.
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import { syncQueueFromServer } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useLikes } from '/src/model/likes'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { usePlayer } from '/src/model/player'
import { useHistory } from '/src/model/history'
import { useAccount } from '/src/model/account'
import { useI18n } from '/src/i18n'
import { itemTrackCount } from '/src/lib/library'

const createOpen = ref(false)
const createFiles = ref([])
const createName = ref('')
const createDescription = ref('')
const createSourceUrl = ref('')
const addOpen = ref(false)
const addPlaylist = ref(null)
const renameOpen = ref(false)
const renamePlaylist = ref(null)
const shareOpen = ref(false)
const sharePlaylist = ref(null)

export function usePlaylistActions() {
  const library = useLibrary()
  const likes = useLikes()
  const tracks = useTrackActions()
  const ui = useUi()
  const player = usePlayer()
  const history = useHistory()
  const router = useRouter()
  const { t } = useI18n()
  const { playlistSharing: sharingOn } = useAccount()

  function contextFor(playlist) {
    return {
      type: 'playlist',
      title: playlist.title,
      cover: playlist.cover || '',
      covers: playlist.covers || [],
      route: { name: 'Playlist', query: { name: playlist.name } },
      // Editing is for the owner: a playlist shared with the user is
      // view-only.
      manual: Boolean(playlist.manual && playlist.mine),
      // The owner hides songs from an imported playlist instead.
      imported: Boolean(playlist.mine && !playlist.manual && !playlist.liked),
      playlistName: playlist.name,
    }
  }

  // `options.tracks`: play the list in this order (the page's sort)
  // instead of the playlist's own.
  async function play(playlist, { tracks: ordered = null, ...options } = {}) {
    await library.loadPlaylistTracks(playlist.name)
    const live = library.findPlaylist(playlist.name) || playlist
    tracks.play(ordered || live.tracks, 0, contextFor(live), options)
  }

  function manuals() {
    // Only the user's own: a playlist shared with them is view-only.
    return library.ownPlaylists.value.filter((item) => item.manual)
  }

  function openCreate(
    files = [],
    { name = '', description = '', sourcePlaylistUrl = '' } = {}
  ) {
    createFiles.value = files.map((item) =>
      typeof item === 'string' ? item : item.file
    )
    createName.value = name
    createDescription.value = description
    createSourceUrl.value = sourcePlaylistUrl
    createOpen.value = true
  }

  function openAddSongs(playlist) {
    addPlaylist.value = playlist
    addOpen.value = true
  }

  function openRename(playlist) {
    renamePlaylist.value = playlist
    renameOpen.value = true
  }

  function openShare(playlist) {
    sharePlaylist.value = playlist
    shareOpen.value = true
  }

  function failed(err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  }

  async function setFollowing(playlist, follow) {
    try {
      if (follow) await API.followPlaylist(playlist.name)
      else await API.unfollowPlaylist(playlist.name)
      await library.refreshPlaylists()
      ui.toast(
        t(follow ? 'sharing.followed' : 'sharing.unfollowed', {
          name: playlist.title,
        }),
        { kind: 'success' }
      )
    } catch (err) {
      failed(err)
    }
  }

  // Clears the "new" marker of a playlist shared with the user.
  async function markSeen(playlist) {
    if (!playlist?.isNew) return
    try {
      await API.markPlaylistSeen(playlist.name)
      await library.refreshPlaylists()
    } catch {
      // Only a marker.
    }
  }

  // Saves a private, editable copy of someone else's playlist (or the
  // user's own); the name it got is returned.
  async function copy(playlist) {
    try {
      const res = await API.copyLibraryPlaylist(playlist.name)
      const created = res.data?.name || playlist.name
      await library.load({ force: true })
      ui.toast(t('sharing.copied', { name: created }), {
        kind: 'success',
        action: {
          label: t('sharing.open'),
          run: () =>
            router.push({ name: 'Playlist', query: { name: created } }),
        },
      })
      return created
    } catch (err) {
      failed(err)
      return ''
    }
  }

  // An imported playlist becomes a Library one: editable, no longer kept
  // in step with its Spotify / YouTube Music source.
  async function detach(playlist) {
    const ok = await ui.confirm({
      title: t('sharing.detachTitle', { name: playlist.title }),
      body: t('sharing.detachBody'),
      confirmLabel: t('sharing.detach'),
    })
    if (!ok) return false
    try {
      await API.detachLibraryPlaylist(playlist.name)
      await library.load({ force: true })
      ui.toast(t('sharing.detached', { name: playlist.title }), {
        kind: 'success',
      })
      return true
    } catch (err) {
      failed(err)
      return false
    }
  }

  async function createNamed(
    name,
    files = [],
    { sourcePlaylistUrl = '' } = {}
  ) {
    try {
      const res = await API.createLibraryPlaylist(name)
      const created = res.data?.name || name
      if (files.length) {
        await API.editLibraryPlaylistTracks(created, {
          add: files,
          sourcePlaylistUrl,
        })
      }
      await library.load({ force: true })
      ui.toast(t('playlists.created', { name: created }), { kind: 'success' })
      return created
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
      throw err
    }
  }

  async function renameNamed(playlist, newName, resetDisplayName = false) {
    try {
      const res = await API.renameLibraryPlaylist(
        playlist.name,
        newName,
        resetDisplayName
      )
      const renamed = res.data?.name || newName
      const displayName = res.data?.display_name || renamed
      const previous = playlist.name
      history.retitlePlaylist(previous, renamed, displayName)
      const ctx = player.context.value
      if (
        ctx?.type === 'playlist' &&
        (ctx.playlistName === previous ||
          ctx.title === previous ||
          ctx.route?.query?.name === previous)
      ) {
        player.context.value = {
          ...ctx,
          title: displayName,
          playlistName: renamed,
          route: { name: 'Playlist', query: { name: renamed } },
        }
      }
      await library.load({ force: true })
      ui.toast(t('playlists.renamed', { name: displayName }), {
        kind: 'success',
      })
      return renamed
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
      throw err
    }
  }

  async function addFiles(playlist, files) {
    const names = files.map((item) =>
      typeof item === 'string' ? item : item.file
    )
    try {
      const res = await API.editLibraryPlaylistTracks(playlist.name, {
        add: names,
      })
      // The server skips what the playlist already has: report what it did.
      const added = Number(res.data?.added ?? names.length)
      await library.load({ force: true })
      ui.toast(
        added
          ? t('playlists.added', { count: added, name: playlist.title })
          : t('playlists.alreadyIn', { name: playlist.title }),
        { kind: 'success' }
      )
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
    }
  }

  async function removeFiles(playlist, files) {
    const names = files.map((item) =>
      typeof item === 'string' ? item : item.file
    )
    try {
      await API.editLibraryPlaylistTracks(playlist.name, { remove: names })
      await library.load({ force: true })
      ui.toast(t('playlists.removedTrack', { name: playlist.title }), {
        kind: 'success',
      })
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
    }
  }

  // An imported playlist follows its source: hiding a song takes it out
  // and keeps it out when the watch or the link brings it back. The song
  // stays in the library.
  async function hideFiles(playlist, files) {
    const names = files.map((item) =>
      typeof item === 'string' ? item : item.file
    )
    try {
      const res = await API.changeHiddenPlaylistSongs(playlist.name, {
        hide: names,
      })
      const keys = res.data?.keys || []
      await library.load({ force: true })
      ui.toast(t('playlists.hiddenTrack', { name: playlist.title }), {
        kind: 'success',
        action: keys.length
          ? {
              label: t('common.undo'),
              run: () => showHidden(playlist, keys, { quiet: true }),
            }
          : undefined,
      })
      return true
    } catch (err) {
      failed(err)
      return false
    }
  }

  // Puts hidden songs back; one whose file is gone returns the next time
  // the playlist downloads what it is missing.
  async function showHidden(playlist, keys, { quiet = false } = {}) {
    try {
      const res = await API.changeHiddenPlaylistSongs(playlist.name, {
        show: keys,
      })
      await library.load({ force: true })
      if (!quiet) {
        const restored = Number(res.data?.restored ?? keys.length)
        ui.toast(
          t(restored ? 'playlists.unhidden' : 'playlists.unhiddenLater', {
            name: playlist.title,
          }),
          { kind: 'success' }
        )
      }
      return true
    } catch (err) {
      failed(err)
      return false
    }
  }

  function addMenuItems(files) {
    const list = Array.isArray(files) ? files : [files]
    const items = [
      { heading: t('playlists.addTo') },
      ...manuals().map((playlist) => ({
        label: playlist.title,
        icon: 'playlist',
        action: () => addFiles(playlist, list),
      })),
      {
        label: t('playlists.new'),
        icon: 'plus',
        action: () => openCreate(list),
      },
    ]
    return items
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

  // Deleting the liked songs playlist would delete songs from disk, so it
  // only ever means "unlike everything" (the server enforces this too).
  async function removeLikes() {
    const ok = await ui.confirm({
      title: t('likes.removeAllTitle'),
      body: t('likes.removeAllBody'),
      confirmLabel: t('likes.removeAll'),
      danger: true,
    })
    if (!ok) return false
    const done = await likes.clear()
    if (done) ui.toast(t('likes.cleared'), { kind: 'success' })
    return done
  }

  async function remove(playlist) {
    if (playlist.liked) return removeLikes()
    const ok = await ui.confirm({
      title: t('confirm.deletePlaylistTitle', { name: playlist.name }),
      body: playlist.manual
        ? t('confirm.deleteManualPlaylistBody')
        : t('confirm.deletePlaylistBody'),
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

  // What someone else's playlist offers: play it, follow it, keep a copy.
  function favoriteAction(playlist) {
    return {
      label: t(
        playlist.favorite ? 'playlistFavorites.remove' : 'playlistFavorites.add'
      ),
      icon: playlist.favorite ? 'heart' : 'heart-outline',
      action: async () => {
        try {
          await API.setPlaylistFavorite(playlist.name, !playlist.favorite)
          await library.refreshPlaylists()
        } catch (error) {
          ui.toast(error?.response?.data?.detail || t('toast.actionFailed'), {
            kind: 'error',
          })
        }
      },
    }
  }

  function viewerMenuFor(playlist) {
    const empty = !itemTrackCount(playlist)
    return [
      favoriteAction(playlist),
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
        action: async () => {
          await library.loadPlaylistTracks(playlist.name)
          const live = library.findPlaylist(playlist.name) || playlist
          tracks.enqueue(live.tracks)
        },
      },
      { divider: true },
      {
        label: t('sharing.follow'),
        icon: 'heart-outline',
        hidden: playlist.visibility !== 'public' || playlist.followed,
        action: () => setFollowing(playlist, true),
      },
      {
        label: t('sharing.unfollow'),
        icon: 'heart',
        hidden: !playlist.followed,
        action: () => setFollowing(playlist, false),
      },
      {
        label: t('sharing.saveCopy'),
        icon: 'copy',
        action: () => copy(playlist),
      },
      {
        label: t('library.downloadZip'),
        icon: 'zip',
        hidden: empty,
        action: () => tracks.downloadZip(playlist.tracks),
      },
    ]
  }

  function menuFor(playlist, { hide = [] } = {}) {
    if (!playlist.mine) return viewerMenuFor(playlist)
    const batch = playlist.batch
    const empty = !itemTrackCount(playlist)
    const imported = !playlist.manual && !playlist.liked
    return [
      favoriteAction(playlist),
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
        action: async () => {
          await library.loadPlaylistTracks(playlist.name)
          const live = library.findPlaylist(playlist.name) || playlist
          tracks.enqueue(live.tracks)
        },
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
        label: t('playlists.addSongs'),
        icon: 'plus',
        hidden: !playlist.manual,
        action: () => openAddSongs(playlist),
      },
      {
        label: t('playlists.rename'),
        icon: 'pencil',
        hidden: playlist.liked,
        action: () => openRename(playlist),
      },
      {
        label: t('playlistNames.restore'),
        icon: 'refresh',
        hidden:
          playlist.manual || playlist.liked || playlist.title === playlist.name,
        action: () => renameNamed(playlist, '', true),
      },
      {
        label: t('sharing.detach'),
        icon: 'link',
        hidden: !imported || !playlist.fileCount,
        action: () => detach(playlist),
      },
      {
        label: t('sharing.share'),
        icon: 'share',
        hidden: playlist.liked || !sharingOn.value,
        action: () => openShare(playlist),
      },
      {
        label: t('library.downloadZip'),
        icon: 'zip',
        hidden: empty,
        action: () => tracks.downloadZip(playlist.tracks),
      },
      { divider: true },
      {
        label: playlist.liked ? t('likes.removeAll') : t('playlists.delete'),
        icon: 'trash',
        danger: true,
        action: () => remove(playlist),
      },
    ]
  }

  return {
    contextFor,
    play,
    downloadMissing,
    watch,
    remove,
    menuFor,
    manuals,
    openCreate,
    openAddSongs,
    openRename,
    openShare,
    setFollowing,
    markSeen,
    copy,
    detach,
    createNamed,
    renameNamed,
    addFiles,
    removeFiles,
    hideFiles,
    showHidden,
    addMenuItems,
    createOpen,
    createFiles,
    createName,
    createDescription,
    createSourceUrl,
    addOpen,
    addPlaylist,
    renameOpen,
    renamePlaylist,
    shareOpen,
    sharePlaylist,
  }
}
