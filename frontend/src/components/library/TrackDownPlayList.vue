<template>
  <div class="flex flex-col gap-3">
    <!-- Selection toolbar: "All"/"New" quick-select chips, and - once
         something is selected - the count, "Download selected" and a way
         to clear. See TOOLBAR_NONE/FIXED/LAZY below for when it shows. -->
    <div
      v-if="selectable && toolbarVisible"
      class="flex flex-wrap items-center gap-3"
    >
      <UiChips
        :model-value="activeChip"
        :items="chips"
        @update:model-value="onChipClick"
      />
      <span v-if="selected.size" class="ml-auto flex items-center gap-2">
        <span class="tabular text-sm text-muted">{{
          t('library.selectedCount', { count: selected.size })
        }}</span>
        <UiButton
          size="sm"
          variant="primary"
          icon="download"
          :loading="downloading"
          @click="downloadSelected"
        >
          {{ t('link.downloadSelected') }}
        </UiButton>
        <UiIconButton
          icon="x"
          :label="t('library.clearSelection')"
          size="sm"
          @click="clearSelection"
        />
      </span>
    </div>

    <div class="-mx-3 flex flex-col">
      <TrackDownPlayHeader :selectable="selectable" :hide-album="hideAlbum" />
      <TrackDownPlay
        v-for="(song, i) in songs"
        :key="keyOf(song, i)"
        :song="song"
        :index="i"
        :queue="queue"
        :context="context"
        :selectable="selectable"
        :selected="selected.has(keyOf(song, i))"
        :marked="!!markedKey && keyOf(song, i) === markedKey"
        :hide-album="hideAlbum"
        :search-links="searchLinks"
        @toggle="toggleSelected(keyOf(song, i))"
      />
    </div>
  </div>
</template>

<script>
// The three `toolbarMode` values below - a plain <script> block so they're
// real named exports (`import { TOOLBAR_LAZY } from '.../TrackDownPlayList.vue'`),
// not just magic strings a caller has to know/copy correctly. Vue's SFC
// compiler shares this block's scope with <script setup> below, so no
// import is needed to use them there too.
export const TOOLBAR_NONE = 'none'
export const TOOLBAR_FIXED = 'fixed'
export const TOOLBAR_LAZY = 'lazy'
</script>

<script setup>
// A list of TrackDownPlay rows (download + library-play + preview), with
// optional multi-select: a checkbox per row and, above the grid, "All"/
// "New" quick-select chips plus a right-aligned "Download selected" once
// something is checked. "New" (not yet in the library) only shows up when
// it would select a *different* set of songs than "All" - hidden when
// every song is new (nothing downloaded yet) or none is (all downloaded).
// Selection state (which rows are checked, and the download-selected
// action) lives entirely in here - a caller just drops this in with a
// list of songs and, if it wants selection at all, sets `selectable`.
//
// Props:
// - `songs` (array, required): the song objects to render, one
//   TrackDownPlay row each, in this order.
// - `selectable` (boolean, default false): show a checkbox on every row
//   and, per `toolbarMode` below, the selection toolbar described above.
//   Off, this is just a plain download/play list - same as using
//   TrackDownPlay directly.
// - `toolbarMode` (one of TOOLBAR_NONE/TOOLBAR_FIXED/TOOLBAR_LAZY,
//   default TOOLBAR_FIXED): when to show the "All"/"New"/"Download
//   selected" bar above the grid. Ignored when `selectable` is off
//   (there is nothing to select, so no toolbar regardless of this).
//     - TOOLBAR_NONE ('none'): never show it. Use this when a page wants
//       the checkboxes visible but its own bar elsewhere (a different
//       layout, extra actions...) - selection still works row by row,
//       just with nothing controlling it from above.
//     - TOOLBAR_FIXED ('fixed'): always show it.
//     - TOOLBAR_LAZY ('lazy'): hidden until at least one row is ticked,
//       then shown for as long as the selection stays non-empty - a
//       quiet list until the user starts picking rows.
//   A page that needs to drive selection externally (its own "select
//   all", reading which songs are checked) doesn't fit this wrapper;
//   use TrackDownPlay directly instead, the way TopSongsPanel does.
// - `queue` (array, default []): the library tracks a row's play button
//   queues from (typically this list's other already-downloaded songs,
//   in order) - forwarded to every TrackDownPlay as-is.
// - `context` (object, default null): where that queue is "playing
//   from", for the player - forwarded to every TrackDownPlay as-is.
// - `collectionName` (string, default ''): the `{name}` in the "Queued
//   N tracks from {name}" toast after a selected-download. Falls back to
//   a generic "Tracks" when left blank.
// - `markedKey` (string, default ''): the key (`song_id`, else `url`) of
//   one song to highlight like the one playing - e.g. the track a page
//   was opened on. Its row gets `data-marked`, to scroll it into view.
// - `hideAlbum` (boolean, default false): leave out the album column -
//   for a list that is all one album anyway.
//
// Events:
// - `download` (songs, count): after a selected-download request has
//   been sent (not necessarily finished) - for a caller that wants to
//   react too (analytics, closing a modal, ...). The component already
//   shows its own success/error toast; this is purely additional.
//
// Usage:
//   <TrackDownPlayList :songs="chart.tracks.value" selectable />
//   <TrackDownPlayList :songs="album.tracks" :selectable="false" />
//   <TrackDownPlayList
//     :songs="playlist.tracks"
//     selectable
//     :toolbar-mode="TOOLBAR_LAZY"
//   />
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import TrackDownPlay from './TrackDownPlay.vue'
import TrackDownPlayHeader from './TrackDownPlayHeader.vue'
import UiButton from '../ui/UiButton.vue'
import UiChips from '../ui/UiChips.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { jobSongKey, useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'

const props = defineProps({
  songs: { type: Array, required: true },
  selectable: { type: Boolean, default: false },
  toolbarMode: {
    type: String,
    default: TOOLBAR_FIXED,
    validator: (value) =>
      [TOOLBAR_NONE, TOOLBAR_FIXED, TOOLBAR_LAZY].includes(value),
  },
  queue: { type: Array, default: () => [] },
  context: { type: Object, default: null },
  collectionName: { type: String, default: '' },
  markedKey: { type: String, default: '' },
  hideAlbum: { type: Boolean, default: false },
  // Forwarded to every TrackDownPlay as-is (see its own `searchLinks`).
  searchLinks: { type: Boolean, default: true },
})

const emit = defineEmits(['download'])

const { t } = useI18n()
const router = useRouter()
const library = useLibrary()
const dm = useDownloadManager()
const ui = useUi()

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

const selected = ref(new Set())

// NONE never shows it, FIXED always does, LAZY only while something is
// actually ticked (goes back to hidden once the selection empties out -
// not a one-way reveal).
const toolbarVisible = computed(() => {
  if (props.toolbarMode === TOOLBAR_LAZY) return selected.value.size > 0
  return props.toolbarMode === TOOLBAR_FIXED
})

function toggleSelected(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

function clearSelection() {
  selected.value = new Set()
}

// Every row's key, by its real position in `songs` - `newKeys` below
// filters down to a subset of these, so it must reuse them rather than
// re-deriving a key from a position in the filtered subset instead (an
// index a fallback `row-N` key would then be wrong about).
const songKeys = computed(() => props.songs.map((song, i) => keyOf(song, i)))

// A song not yet in the library - what the "New" chip selects.
function isNew(song) {
  const artist = (song.artists || [])[0] || song.artist
  return !library.findTrack(artist, song.name)
}

const newKeys = computed(() =>
  props.songs
    .map((song, i) => (isNew(song) ? songKeys.value[i] : null))
    .filter(Boolean)
)

const allSelected = computed(
  () => props.songs.length > 0 && selected.value.size === props.songs.length
)
const allNewSelected = computed(
  () =>
    newKeys.value.length > 0 &&
    selected.value.size === newKeys.value.length &&
    newKeys.value.every((key) => selected.value.has(key))
)

// Reads as pressed once its own condition is actually true, however that
// was reached (the chip itself, or ticking rows one by one) - never a
// literal "last chip clicked" flag, which could go stale the moment a
// single row is unticked.
const activeChip = computed(() => {
  if (allSelected.value) return 'all'
  if (allNewSelected.value) return 'new'
  return ''
})

// Hidden when it would just repeat "All" - either nothing is new (every
// song already downloaded) or, same as here, nothing has been downloaded
// yet, so "New" and "All" pick the exact same songs.
const chips = computed(() => [
  { id: 'all', label: t('link.filterAll'), count: props.songs.length },
  ...(newKeys.value.length && newKeys.value.length < props.songs.length
    ? [{ id: 'new', label: t('link.filterNew'), count: newKeys.value.length }]
    : []),
])

function onChipClick(id) {
  if (id === 'all') selected.value = new Set(songKeys.value)
  else if (id === 'new') selected.value = new Set(newKeys.value)
}

const downloading = ref(false)

async function downloadSelected() {
  const songs = props.songs.filter((song, i) =>
    selected.value.has(songKeys.value[i])
  )
  if (!songs.length) return
  downloading.value = true
  try {
    const count = await dm.fromSongs(songs)
    clearSelection()
    emit('download', songs, count)
    ui.toast(
      t('toast.queuedTracks', {
        count,
        name: props.collectionName || t('library.tracks'),
      }),
      {
        kind: 'success',
        action: {
          label: t('nav.queue'),
          run: () => router.push({ name: 'Queue' }),
        },
      }
    )
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    downloading.value = false
  }
}
</script>
