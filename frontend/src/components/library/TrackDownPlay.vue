<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors"
    :class="isCurrent ? 'bg-surface' : 'hover:bg-surface'"
    @click="onRowClick"
    @dblclick="play"
  >
    <span
      v-if="index !== null"
      class="flex w-6 items-center justify-center text-[13px] text-faint max-sm:hidden"
    >
      <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
      <template v-else>
        <span class="tabular" :class="track ? 'group-hover:hidden' : ''">{{
          index + 1
        }}</span>
        <button
          v-if="track"
          type="button"
          class="hidden text-fg group-hover:block"
          :aria-label="t('actions.playItem', { name: song.name })"
          @click.stop="play"
        >
          <AppIcon name="play" :size="14" />
        </button>
      </template>
    </span>

    <button
      v-if="track"
      type="button"
      class="relative shrink-0"
      :aria-label="t('actions.playItem', { name: song.name })"
      @click.stop="play"
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
          :class="isCurrent ? 'text-accent' : ''"
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
      class="tabular hidden w-12 text-right text-[13px] text-muted sm:block"
    >
      {{ song.duration ? formatDuration(song.duration) : '' }}
    </span>
    <!-- Not downloaded: the download button, with its progress and retry;
         downloaded: the "In library" label. Playing is on the left. -->
    <div class="flex w-28 shrink-0 justify-end">
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
// Deliberately standalone: it borrows the look of SongRow and the behaviour
// of TrackList without importing or editing either, so neither grid can be
// affected by it. It takes a *song* (what a search or link result is), not a
// library track, and finds the file behind it once it has been downloaded.
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import DownloadState from '../search/DownloadState.vue'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useTrackActions } from '/src/model/trackActions'
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
  // Where the queue comes from, for the player's "playing from".
  context: { type: Object, default: null },
})

const { t } = useI18n()
const library = useLibrary()
const player = usePlayer()
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

function play() {
  if (!track.value) return
  const start = props.queue.findIndex((item) => item.file === track.value.file)
  if (start < 0) actions.play([track.value], 0, props.context)
  else actions.play(props.queue, start, props.context)
}

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick() {
  if (window.matchMedia('(pointer: coarse)').matches) play()
}
</script>
