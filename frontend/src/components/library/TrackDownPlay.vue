<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors"
    :class="highlighted ? 'bg-surface' : 'hover:bg-surface'"
    @click="onRowClick"
    @dblclick="ensurePlaying"
  >
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
            :stroke-dashoffset="ringOffset(preview.progress.value)"
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
        :src="song.cover_url"
        :name="song.album_name || song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
    </button>
    <CoverArt
      v-else
      :src="song.cover_url"
      :name="song.album_name || song.name"
      rounded="rounded-[8px]"
      :letter-size="14"
      class="size-11"
    />

    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <span
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
        }}<span v-if="song.album_name" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span class="hidden w-[30%] truncate text-[13px] text-muted lg:block">{{
      song.album_name
    }}</span>
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
// clip, when it has one (`song.preview_url`): on the row itself, without the
// built-in player - see model/preview.js.
//
// Deliberately standalone: it borrows the look of SongRow and the behaviour
// of TrackList without importing or editing either, so neither grid can be
// affected by it. It takes a *song* (what a search or link result is), not a
// library track, and finds the file behind it once it has been downloaded.
import { computed, onBeforeUnmount, watch } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import DownloadState from '../search/DownloadState.vue'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePreview } from '/src/model/preview'
import { useTrackActions } from '/src/model/trackActions'
import { formatDuration } from '/src/lib/format'
import {
  PREVIEW_RING_LENGTH,
  PREVIEW_RING_RADIUS,
  previewUrl,
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
})

const { t } = useI18n()
const library = useLibrary()
const player = usePlayer()
const preview = usePreview()
const actions = useTrackActions()

const artists = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
// The library track behind the song once it's downloaded - the library
// refreshes itself shortly after a download finishes, and this follows.
const track = computed(() =>
  library.findTrack(
    (props.song.artists || [])[0] || props.song.artist,
    props.song.name
  )
)
const isCurrent = computed(
  () => !!track.value && player.currentTrack.value?.file === track.value.file
)

// A song that isn't in the library but has a clip to listen to.
const previewable = computed(() => !track.value && !!previewUrl(props.song))
const songId = computed(() => String(props.song.song_id || ''))
const previewActive = computed(
  () => previewable.value && preview.activeId.value === songId.value
)
const previewPlaying = computed(
  () => previewActive.value && preview.isPlaying.value
)
const previewLoading = computed(
  () => previewActive.value && preview.isLoading.value
)
// Something on this row plays: the downloaded song, or its clip.
const playable = computed(() => !!track.value || previewable.value)
const highlighted = computed(() => isCurrent.value || previewActive.value)
const playLabel = computed(() =>
  t(
    track.value
      ? 'actions.playItem'
      : previewPlaying.value
        ? 'actions.pausePreview'
        : 'actions.playPreview',
    { name: props.song.name }
  )
)

function play() {
  if (!track.value) return
  const start = props.queue.findIndex((item) => item.file === track.value.file)
  if (start < 0) actions.play([track.value], 0, props.context)
  else actions.play(props.queue, start, props.context)
}

// The play button: the song from the library, or - not downloaded yet - its
// clip, which the same button pauses again.
function toggle() {
  if (track.value) play()
  else if (previewable.value) preview.toggle(props.song)
}

// A double click makes sure the song plays; it never pauses a clip.
function ensurePlaying() {
  if (track.value) play()
  else if (previewable.value && !previewPlaying.value) {
    preview.toggle(props.song)
  }
}

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick() {
  if (window.matchMedia('(pointer: coarse)').matches) toggle()
}

// Once the song has been downloaded the row plays the real thing, so the
// clip ends; a row that goes away takes its clip with it.
watch(track, (found) => {
  if (found) preview.stopFor(songId.value)
})
onBeforeUnmount(() => preview.stopFor(songId.value))
</script>
