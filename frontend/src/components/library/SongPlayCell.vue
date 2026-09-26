<template>
  <!-- A selectable list's number cell (a link's tracks, an artist's top
       songs): the number, turning into play on hover when the song plays -
       from the library once downloaded, else its 30 s preview clip, with a
       ring that fills as the clip goes. On a phone, where the number isn't
       shown, just the play button. -->
  <span
    class="flex w-6 shrink-0 items-center justify-center text-[13px] text-faint"
    :class="playable ? '' : 'max-sm:hidden'"
  >
    <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
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
      <span
        class="tabular max-sm:hidden"
        :class="playable ? 'group-hover:hidden' : ''"
        >{{ index + 1 }}</span
      >
      <button
        v-if="playable"
        type="button"
        class="text-fg sm:hidden sm:group-hover:block"
        :aria-label="playLabel"
        :title="track ? '' : t('actions.previewLabel')"
        @click.stop="toggle"
      >
        <AppIcon name="play" :size="14" />
      </button>
    </template>
  </span>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import EqBars from '../ui/EqBars.vue'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import {
  PREVIEW_RING_LENGTH,
  PREVIEW_RING_RADIUS,
  ringOffset,
} from '/src/lib/preview'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  index: { type: Number, required: true },
  // The list's downloaded songs, as library tracks, to queue after this one.
  queue: { type: Array, default: () => [] },
  // The player's "playing from".
  context: { type: Object, default: null },
})

const { t } = useI18n()
const player = usePlayer()
const {
  track,
  isCurrent,
  previewActive,
  previewPlaying,
  previewLoading,
  playable,
  playLabel,
  progress,
  toggle,
} = useSongPlay(props)
</script>
