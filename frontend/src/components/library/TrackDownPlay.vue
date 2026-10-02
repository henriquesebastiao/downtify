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
      <!-- A clip that isn't downloaded yet, while it is loaded: play/pause
           with a ring that fills as the clip goes, where the number was. -->
      <button
        v-else-if="previewActive"
        type="button"
        class="relative grid size-6 place-items-center text-fg"
        :aria-label="playLabel"
        @click.stop="toggle"
      >
        <svg
          class="absolute inset-0 size-full -rotate-90"
          viewBox="0 0 24 24"
          fill="none"
          stroke-width="2"
          aria-hidden="true"
        >
          <circle
            cx="12"
            cy="12"
            :r="PREVIEW_RING_RADIUS"
            stroke="currentColor"
            stroke-opacity="0.25"
          />
          <circle
            cx="12"
            cy="12"
            :r="PREVIEW_RING_RADIUS"
            class="stroke-accent"
            stroke-linecap="round"
            :stroke-dasharray="PREVIEW_RING_LENGTH"
            :stroke-dashoffset="ringOffset(progress)"
            style="transition: stroke-dashoffset 250ms linear"
          />
        </svg>
        <AppIcon
          :name="previewPlaying ? 'pause' : 'play'"
          :size="10"
          :class="previewLoading ? 'animate-pulse' : ''"
        />
      </button>
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
        <TrackArtistLinks
          :artists="song.artists"
          :fallback="song.artist || t('common.unknownArtist')"
          only-known
          :search-missing="searchLinks"
        /><span v-if="song.album_name && !hideAlbum" class="lg:hidden">
          ·
          <RouterLink
            v-if="albumLink"
            :to="albumLink"
            class="hover:text-fg hover:underline"
            @click.stop
            @dblclick.stop
            >{{ song.album_name }}</RouterLink
          ><template v-else>{{ song.album_name }}</template></span
        >
      </p>
    </div>
    <span
      v-if="!hideAlbum"
      class="hidden w-[30%] truncate text-[13px] text-muted lg:block"
    >
      <!-- The album's Library page, or a search for it (albumLinkFor). -->
      <RouterLink
        v-if="albumLink"
        :to="albumLink"
        class="hover:text-fg hover:underline"
        @click.stop
        @dblclick.stop
        >{{ song.album_name }}</RouterLink
      >
      <template v-else>{{ song.album_name }}</template>
    </span>
    <span
      class="tabular relative hidden w-12 text-right text-[13px] text-muted sm:block"
    >
      <!-- Only a clip to hear (not downloaded): its length gives way to
           "Preview" while the row is hovered, and for as long as the clip is
           loaded (the row stays highlighted then, like a hovered one, with
           the mouse gone). The length is hidden, not removed, so nothing
           moves; the label sits on the cell's right edge and may run a little
           to its left, over the gap before it. -->
      <span
        :class="
          previewable
            ? previewActive
              ? 'invisible'
              : 'group-hover:invisible'
            : ''
        "
        >{{ song.duration ? formatDuration(song.duration) : '' }}</span
      >
      <span
        v-if="previewable"
        class="pointer-events-none absolute inset-y-0 right-0 items-center text-[10px] font-semibold tracking-[0.06em] whitespace-nowrap uppercase"
        :class="previewActive ? 'flex' : 'hidden group-hover:flex'"
        >{{ t('actions.previewLabel') }}</span
      >
    </span>
    <!-- Not downloaded: the download button, with its progress and retry;
         downloaded: the "In library" label. Playing is on the left. A click
         here is the download's own, never the row's (a tap plays). -->
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
// Until the song is downloaded the same affordances play its 30 s preview
// clip: on the row itself, without the built-in player - see
// model/songPlay.js and model/preview.js.
//
// Deliberately standalone: it borrows the look of SongRow and the behaviour
// of TrackList without importing or editing either, so neither grid can be
// affected by it. It takes a *song* (what a search or link result is), not a
// library track, and finds the file behind it once it has been downloaded.
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import DownloadState from '../search/DownloadState.vue'
import TrackArtistLinks from './TrackArtistLinks.vue'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { deezerImage } from '/src/lib/deezerImage'
import { formatDuration } from '/src/lib/format'
import { albumLinkFor } from '/src/lib/library'
import {
  PREVIEW_RING_LENGTH,
  PREVIEW_RING_RADIUS,
  ringOffset,
} from '/src/lib/preview'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // A song from a search/link/top-songs result.
  song: { type: Object, required: true },
  // Its position in the list, shown as the number; `null` hides it.
  index: { type: Number, default: null },
  // The library tracks playing this song starts a queue from (typically the
  // list's other downloaded songs, in order). Without it, just this song.
  queue: { type: Array, default: () => [] },
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
  // Whether an artist or album the Library doesn't have links to a search
  // for it. Off where a page must not send anyone to Search (Discover):
  // those names stay plain text, while what the Library has still links.
  searchLinks: { type: Boolean, default: true },
})

const emit = defineEmits(['toggle'])

const { t } = useI18n()
const player = usePlayer()
const library = useLibrary()

// The album name links to the album in the Library, or to a search for it.
// The albums index is fetched once and shared by every row.
const albumLink = computed(() =>
  albumLinkFor(library.albums.value, props.song, {
    search: props.searchLinks,
  })
)
onMounted(() => {
  if (props.song.album_name && !props.hideAlbum)
    library.ensureAlbums().catch(() => {})
})
const {
  isCurrent,
  previewable,
  previewActive,
  previewPlaying,
  previewLoading,
  playable,
  highlighted: playing,
  playLabel,
  progress,
  toggle,
  ensurePlaying,
} = useSongPlay(props)

// A Deezer cover at its medium size, for the 44px thumbnail - display only:
// the song's own `cover_url` is what its download embeds.
const cover = computed(() => deezerImage(props.song.cover_url))
// Lit up while it plays (or its clip does), and when the caller points at it.
const highlighted = computed(() => props.marked || playing.value)

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick() {
  if (window.matchMedia('(pointer: coarse)').matches) toggle()
}
</script>
