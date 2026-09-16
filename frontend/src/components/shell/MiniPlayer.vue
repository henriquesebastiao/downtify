<template>
  <Transition name="now-playing">
    <div
      v-if="track && !nowPlaying.isOpen.value"
      class="relative flex h-16 items-center gap-3 overflow-hidden rounded-[16px] border border-line-3 bg-glass pr-2 pl-2 shadow-float backdrop-blur-xl md:h-[76px] md:gap-5 md:rounded-[18px] md:pr-5 md:pl-3"
    >
      <!-- Progress: a hairline on phones, a scrubber on desktop. -->
      <div class="absolute inset-x-3 bottom-0 h-0.5 bg-line-2 md:hidden">
        <div
          class="h-full bg-accent"
          :style="{ width: `${player.progressPct.value}%` }"
        />
      </div>
      <div class="absolute inset-x-0 -top-2 hidden md:block">
        <SliderBar
          :model-value="scrub ?? player.currentTime.value"
          :max="player.duration.value || 1"
          :label="t('player.seek')"
          :value-text="formatDuration(player.currentTime.value)"
          :hit-height="16"
          track-class="bg-transparent"
          fill-class="bg-accent"
          thumb-class="bg-accent"
          @update:model-value="(v) => (scrub = v)"
          @commit="commitSeek"
        />
      </div>

      <button
        type="button"
        class="flex min-w-0 flex-1 items-center gap-3 text-left md:w-[300px] md:flex-none"
        :aria-label="t('player.openNowPlaying')"
        @click="nowPlaying.open()"
      >
        <CoverArt
          :src="track.hasCover ? track.cover : ''"
          :name="track.album || track.title"
          rounded="rounded-[10px]"
          :letter-size="18"
          :icon-size="18"
          class="size-11 md:size-[52px]"
        />
        <span class="flex min-w-0 flex-col">
          <span class="flex items-center gap-2">
            <span class="truncate text-sm font-semibold">{{
              track.title
            }}</span>
            <EqBars
              v-if="player.isPlaying.value"
              :size="10"
              class="hidden md:inline-flex"
            />
          </span>
          <span class="truncate text-xs text-muted">
            {{ [track.artist, track.album].filter(Boolean).join(' · ') }}
          </span>
        </span>
      </button>

      <div class="flex items-center justify-center gap-1 md:flex-1 md:gap-3">
        <UiIconButton
          icon="shuffle"
          :label="t('player.shuffle')"
          :active="player.shuffle.value"
          toggle
          class="hidden md:inline-flex"
          @click="player.toggleShuffle()"
        />
        <UiIconButton
          icon="prev"
          :label="t('player.previous')"
          class="hidden md:inline-flex"
          @click="player.prev()"
        />
        <button
          type="button"
          class="flex size-11 items-center justify-center rounded-full text-fg md:bg-invert md:text-on-invert md:transition-transform md:hover:scale-105"
          :aria-label="
            player.isPlaying.value ? t('player.pause') : t('player.play')
          "
          @click="player.toggle()"
        >
          <span
            v-if="player.isBuffering.value && player.isPlaying.value"
            class="size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
          />
          <AppIcon
            v-else
            :name="player.isPlaying.value ? 'pause' : 'play'"
            :size="18"
          />
        </button>
        <UiIconButton
          icon="next"
          :label="t('player.next')"
          @click="player.next()"
        />
        <UiIconButton
          :icon="player.repeatMode.value === 'one' ? 'repeat-one' : 'repeat'"
          :label="repeatLabel"
          :active="player.repeatMode.value !== 'off'"
          toggle
          class="hidden md:inline-flex"
          @click="player.cycleRepeat()"
        />
      </div>

      <div class="hidden items-center justify-end gap-1 md:flex md:w-[300px]">
        <span class="tabular mr-2 hidden text-xs text-muted lg:inline">
          {{ formatDuration(player.currentTime.value) }} /
          {{ formatDuration(player.duration.value) }}
        </span>
        <UiIconButton
          icon="lyrics"
          :label="t('player.lyrics')"
          size="sm"
          @click="nowPlaying.open('lyrics')"
        />
        <UiIconButton
          icon="queue"
          :label="t('player.upNext')"
          size="sm"
          @click="nowPlaying.open('queue')"
        />
        <VolumeControl class="hidden lg:flex" width="w-20" />
        <UiIconButton
          icon="expand"
          :label="t('player.openNowPlaying')"
          size="sm"
          @click="nowPlaying.open()"
        />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import SliderBar from '../player/SliderBar.vue'
import VolumeControl from '../player/VolumeControl.vue'
import { usePlayer } from '/src/model/player'
import { useNowPlaying } from '/src/model/ui'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const nowPlaying = useNowPlaying()
const { t } = useI18n()
const scrub = ref(null)

const track = computed(() => player.currentTrack.value)

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}
</script>
