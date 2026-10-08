<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors"
    :class="
      selected ? 'bg-accent/8' : highlighted ? 'bg-surface' : 'hover:bg-surface'
    "
    :data-marked="marked || undefined"
    @click="onRowClick"
    @dblclick="ensurePlaying"
  >
    <button
      v-if="selectable"
      type="button"
      role="checkbox"
      :aria-checked="selected"
      :aria-label="t('library.selectTrack', { title: song.name })"
      class="flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border-[1.5px] transition-colors"
      :class="
        selected
          ? 'border-accent bg-accent text-on-accent'
          : 'border-line-3 hover:border-fg-3'
      "
      @click.stop="emit('toggle')"
      @dblclick.stop
    >
      <AppIcon v-if="selected" name="check" :size="13" stroke-width="3" />
    </button>
    <span
      v-if="index !== null"
      class="flex w-6 items-center justify-center text-[13px] text-faint max-sm:hidden"
    >
      <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
      <!-- A stream being resolved, where the number was. -->
      <AppIcon
        v-else-if="loading"
        name="refresh"
        :size="14"
        class="animate-spin text-fg"
      />
      <template v-else>
        <span class="tabular" :class="playable ? 'group-hover:hidden' : ''">{{
          index + 1
        }}</span>
        <button
          v-if="playable"
          type="button"
          class="hidden text-fg group-hover:block"
          :aria-label="playLabel"
          @click.stop="toggle"
        >
          <AppIcon name="play" :size="14" />
        </button>
      </template>
    </span>

    <button
      v-if="playable"
      type="button"
      class="shrink-0"
      :aria-label="playLabel"
      @click.stop="toggle"
    >
      <CoverArt
        :src="cover"
        :name="song.album_name || song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
    </button>
    <CoverArt
      v-else
      :src="cover"
      :name="song.album_name || song.name"
      rounded="rounded-[8px]"
      :letter-size="14"
      class="size-11"
    />

    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <RouterLink
          v-if="to"
          :to="to"
          class="truncate text-sm font-semibold hover:underline"
          :class="highlighted ? 'text-accent' : ''"
          @click.stop
          @dblclick.stop
          >{{ song.name }}</RouterLink
        >
        <span
          v-else
          class="truncate text-sm font-semibold"
          :class="highlighted ? 'text-accent' : ''"
          >{{ song.name }}</span
        >
        <span
          v-if="song.explicit"
          class="shrink-0 rounded-[3px] bg-muted px-1 text-[9px] leading-[14px] font-bold text-bg"
          :title="t('search.explicit')"
          >E</span
        >
      </p>
      <p class="truncate text-[13px] text-muted">
        {{ artists
        }}<span v-if="song.album_name && !hideAlbum" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span
      v-if="!hideAlbum"
      class="hidden w-[30%] truncate text-[13px] text-muted lg:block"
      >{{ song.album_name }}</span
    >
    <span
      class="tabular hidden w-12 text-right text-[13px] text-muted sm:block"
    >
      {{ song.duration ? formatDuration(song.duration) : '' }}
    </span>
    <!-- Not downloaded: the download button, with its progress and retry;
         downloaded: the "In library" label. Playing is on the left. A click
         here is the download's own, never the row's (a tap plays). -->
    <SimilarButton :artist="firstArtist" :title="song.name" />
    <div class="flex w-28 shrink-0 justify-end" @click.stop @dblclick.stop>
      <DownloadState :song="song" />
    </div>
  </div>
</template>

<script setup>
// One song as a row that downloads, then plays: minimal like a search
// result (SongRow), with the play affordances TrackList has on an album page
// once the song is in the library (the number turns into a play button on
// hover, the cover plays, a double click plays, a tap plays on a touch
// screen). On the right it shows the download state - the button, its
// progress, or the "In library" label - the way a search result does.
//
// Until the song is downloaded the same affordances stream it in full
// from YouTube, always shown in the built-in player - see
// model/songPlay.js and model/stream.js.
//
// Deliberately standalone: it borrows the look of SongRow and the behaviour
// of TrackList without importing or editing either, so neither grid can be
// affected by it. It takes a *song* (what a search or link result is), not a
// library track, and finds the file behind it once it has been downloaded.
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import DownloadState from '../search/DownloadState.vue'
import SimilarButton from '../similar/SimilarButton.vue'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { deezerImage } from '/src/lib/deezerImage'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // A song from a search/link/top-songs result.
  song: { type: Object, required: true },
  // Its position in the list, shown as the number; `null` hides it.
  index: { type: Number, default: null },
  // The library tracks playing this song starts a queue from (typically the
  // list's other downloaded songs, in order). Without it, just this song.
  queue: { type: Array, default: () => [] },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
  // Where the queue comes from, for the player's "playing from".
  context: { type: Object, default: null },
  // Off by default: a caller doing multi-select (e.g. a "download selected"
  // list) turns this on and owns the actual selection state itself - this
  // row only shows the checkbox and reports clicks on it via `toggle`.
  selectable: { type: Boolean, default: false },
  // Whether this row is currently selected. Ignored unless `selectable`.
  selected: { type: Boolean, default: false },
  // Makes the title a link to this route location (e.g. a page about the
  // song); a plain title when unset.
  to: { type: [String, Object], default: null },
  // Highlights the row like the one playing - for a caller pointing at
  // one song in the list (the Finder's, for the track it was opened on).
  marked: { type: Boolean, default: false },
  // Leaves out the album column (and the album after the artists on a
  // narrow screen) - for a list that is all one album anyway.
  hideAlbum: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle'])

const { t } = useI18n()
const player = usePlayer()
const {
  isCurrent,
  loading,
  playable,
  highlighted: playing,
  playLabel,
  toggle,
  ensurePlaying,
} = useSongPlay(props)

const artists = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
const firstArtist = computed(
  () => (props.song.artists || [])[0] || props.song.artist || ''
)
// A Deezer cover at its medium size, for the 44px thumbnail - display only:
// the song's own `cover_url` is what its download embeds.
const cover = computed(() => deezerImage(props.song.cover_url))
// Lit up while it plays, and when the caller points at it.
const highlighted = computed(() => props.marked || playing.value)

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick() {
  if (window.matchMedia('(pointer: coarse)').matches) toggle()
}
</script>
