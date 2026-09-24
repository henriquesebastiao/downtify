// The state behind a list of an artist's top songs: which rows exist and
// what their status is, the selection, the "Create playlist" choice and the
// download. Shared by the top-songs page (a pasted link) and the artist
// page's Top songs tab, which show the same list the same way
// (TopSongsPanel).
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { jobSongKey, useDownloadManager, useProgressTracker } from './download'
import { useLibrary } from './library'
import { useUi } from './ui'
import { topSongsBatchOptions, topSongsPlaylistName } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

// How many of the top songs start out selected.
export const PRESELECTED = 5

/**
 * @param artist a ref to `{ name, cover_url, songs }` (or null while it
 *   loads) - the shape of `GET /api/artists/top_songs/url`.
 * @returns a reactive object (refs already unwrapped) meant to be handed
 *   to `<TopSongsPanel :state>` as is.
 */
export function useTopSongs(artist) {
  const { t } = useI18n()
  const router = useRouter()
  const dm = useDownloadManager()
  const tracker = useProgressTracker()
  const library = useLibrary()
  const ui = useUi()

  const selected = ref(new Set())
  const submitting = ref(false)
  // Off for a first visit; on when this artist's top-songs playlist already
  // exists, so later downloads keep feeding it. Once the switch is touched,
  // that choice wins.
  const playlistChoice = ref(null)
  const playlistExists = computed(
    () =>
      !!artist.value &&
      !!library.findPlaylist(topSongsPlaylistName(artist.value))
  )
  const createPlaylist = computed({
    get: () => playlistChoice.value ?? playlistExists.value,
    set: (value) => {
      playlistChoice.value = value
    },
  })

  // The plays column only appears when the list has counts to show.
  const hasPlays = computed(() =>
    (artist.value?.songs || []).some((song) => song.play_count)
  )

  function keyOf(song, index) {
    return jobSongKey(song) || `row-${index}`
  }

  function statusOf(song) {
    tracker.queueVersion.value
    if (tracker.getBySong(song)) return 'queue'
    const name = (song.artists || [])[0] || song.artist
    return library.hasSong(name, song.name) ? 'library' : 'new'
  }

  const rows = computed(() =>
    (artist.value?.songs || []).map((song, index) => ({
      song,
      index,
      key: keyOf(song, index),
      status: statusOf(song),
    }))
  )

  // What "Download all" sends: everything not already in the library or the
  // queue, in ranking order.
  const newSongs = computed(() =>
    rows.value.filter((row) => row.status === 'new').map((row) => row.song)
  )

  const selectedSongs = computed(() =>
    rows.value
      .filter((row) => selected.value.has(row.key))
      .map((row) => row.song)
  )

  const allSelected = computed(
    () => rows.value.length > 0 && selected.value.size === rows.value.length
  )

  // "Select all" reads as pressed once everything is ticked, like the
  // filter chips on the album and playlist pages; "Clear selection" is an
  // action, so it only shows up while something is selected.
  const selectionChips = computed(() => [
    { id: 'all', label: t('link.selectAll'), count: rows.value.length },
    ...(selected.value.size
      ? [{ id: 'none', label: t('library.clearSelection') }]
      : []),
  ])

  function toggle(key) {
    const next = new Set(selected.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    selected.value = next
  }

  function selectAll() {
    selected.value = new Set(rows.value.map((row) => row.key))
  }

  function onSelectionChip(id) {
    if (id === 'all') selectAll()
    else selected.value = new Set()
  }

  /** Back to a fresh list: the first few rows ticked, the playlist switch
   * following the library again. Call it whenever `artist` is replaced. */
  function reset() {
    playlistChoice.value = null
    selected.value = new Set(
      rows.value.slice(0, PRESELECTED).map((row) => row.key)
    )
  }

  async function download(songs) {
    if (!songs.length) return
    submitting.value = true
    try {
      // The songs go out in ranking order with their rank as the track
      // order, so the M3U keeps the artist's own order even when only some
      // of them are picked.
      const ranked = songs.map((song) => ({
        ...song,
        downtify_track_order: artist.value.songs.indexOf(song),
      }))
      const count = await dm.fromSongs(
        ranked,
        topSongsBatchOptions(artist.value, createPlaylist.value)
      )
      selected.value = new Set()
      ui.toast(t('toast.queuedTracks', { count, name: artist.value.name }), {
        kind: 'success',
        action: {
          label: t('nav.queue'),
          run: () => router.push({ name: 'Queue' }),
        },
      })
    } catch (err) {
      ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
        kind: 'error',
      })
    } finally {
      submitting.value = false
    }
  }

  return reactive({
    artist,
    selected,
    submitting,
    createPlaylist,
    hasPlays,
    rows,
    newSongs,
    selectedSongs,
    allSelected,
    selectionChips,
    toggle,
    selectAll,
    onSelectionChip,
    reset,
    download,
  })
}
