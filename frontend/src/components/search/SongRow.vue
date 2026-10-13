<template>
  <div
    class="group flex h-16 items-center gap-3 rounded-[12px] px-3 transition-colors hover:bg-surface"
    @click="onRowClick"
    @dblclick="ensurePlaying"
  >
    <span
      v-if="index !== null"
      class="tabular w-6 text-center text-[13px] text-faint max-sm:hidden"
    >
      {{ index + 1 }}
    </span>
    <button
      type="button"
      class="relative shrink-0"
      :aria-label="play.playLabel.value"
      :disabled="!play.playable.value"
      @click.stop="play.toggle()"
    >
      <CoverArt
        :src="song.cover_url"
        :name="song.album_name || song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
      <span
        v-if="play.playable.value"
        class="absolute inset-0 hidden items-center justify-center rounded-[8px] bg-black/45 text-white group-hover:flex"
        :class="play.isCurrent.value ? '!flex' : ''"
      >
        <AppIcon
          v-if="play.loading.value"
          name="refresh"
          :size="16"
          class="animate-spin"
        />
        <AppIcon v-else :name="overlayIcon" :size="16" />
      </span>
    </button>
    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <span class="truncate text-sm font-semibold">{{ song.name }}</span>
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
    <a
      v-if="sourceUrl"
      :href="sourceUrl"
      target="_blank"
      rel="noopener"
      class="hidden size-8 items-center justify-center rounded-control text-faint hover:bg-surface-2 hover:text-fg sm:flex lg:opacity-0 lg:group-hover:opacity-100"
      :title="openSourceLabel"
      :aria-label="openSourceLabel"
    >
      <AppIcon name="arrow-up-right" :size="16" />
    </a>
    <div class="flex w-40 shrink-0 items-center justify-end gap-2">
      <SimilarButton :artist="firstArtist" :title="song.name" filled />
      <DownloadState :song="song" />
    </div>
  </div>
</template>

<script setup>
// A search result: full playback on the cover (from the library, else
// streamed) without downloading anything, and the wand next to the
// download button, styled like it (as on Charts).
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import DownloadState from './DownloadState.vue'
import SimilarButton from '../similar/SimilarButton.vue'
import { formatDuration } from '/src/lib/format'
import { useSongPlay } from '/src/model/songPlay'
import { usePlayer } from '/src/model/player'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, default: null },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
})
const { t } = useI18n()
const player = usePlayer()

// Playing works like every other track row: a downloaded song plays in
// full through the built-in player, anything else streams in full.
const play = useSongPlay(props)
const overlayIcon = computed(() =>
  play.isCurrent.value && player.isPlaying.value ? 'pause' : 'play'
)
const { toggle, ensurePlaying } = play

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick() {
  if (window.matchMedia('(pointer: coarse)').matches) toggle()
}

const artists = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)
const firstArtist = computed(
  () => (props.song.artists || [])[0] || props.song.artist || ''
)
const sourceUrl = computed(() => {
  const url = String(props.song.url || '')
  return /^https?:\/\//.test(url) ? url : ''
})
// Charts' Deezer tracks reuse this row; their link opens Deezer, not
// YouTube Music.
const openSourceLabel = computed(() =>
  props.song.source === 'deezer' ? t('link.openDeezer') : t('search.openSource')
)
</script>
