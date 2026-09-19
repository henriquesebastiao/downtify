<template>
  <Transition name="now-playing">
    <div
      v-if="track && !nowPlaying.isOpen.value"
      class="relative flex h-16 items-center gap-3 overflow-hidden rounded-[16px] border border-line-3 bg-glass pr-2 pl-2 shadow-float backdrop-blur-xl md:h-[76px] md:gap-5 md:rounded-[18px] md:pr-5 md:pl-3"
    >
      <!-- Progress: a hairline on phones, a scrubber on desktop. -->
      <div class="absolute inset-x-3 bottom-0 h-0.5 bg-line-2 md:hidden">
        <div class="h-full bg-accent" :style="{ width: `${smoothPercent}%` }" />
      </div>
      <div class="absolute inset-x-0 -top-2 hidden md:block">
        <SliderBar
          :model-value="scrub ?? player.currentTime.value"
          :max="player.duration.value || 1"
          :label="t('player.seek')"
          :value-text="formatDuration(player.currentTime.value)"
          :hit-height="16"
          :playing="player.isPlaying.value"
          track-class="bg-transparent"
          fill-class="bg-accent"
          thumb-class="bg-accent"
          @update:model-value="(v) => (scrub = v)"
          @commit="commitSeek"
        />
      </div>

      <!-- The heart sits beside the button that opens Now playing, not
           inside it, so tapping it never opens the overlay. -->
      <div
        class="flex min-w-0 flex-1 items-center gap-1 md:w-[300px] md:flex-none"
      >
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center gap-3 text-left"
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
        <!-- Phones have no room for it beside the transport buttons;
             the rows and the full player carry the heart there. -->
        <span class="hidden sm:contents"
          ><LikeButton :file="track.file"
        /></span>
      </div>

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
        <!-- Never wraps, and keeps one width for the whole track: the
             invisible copy is the widest the text will get, so the
             controls beside it don't shift as it ticks past 10:00. -->
        <span
          class="tabular mr-2 hidden shrink-0 text-xs whitespace-nowrap text-muted lg:inline-grid"
        >
          <span class="invisible col-start-1 row-start-1" aria-hidden="true">{{
            clockSizer
          }}</span>
          <span class="col-start-1 row-start-1 text-right"
            >{{ formatDuration(player.currentTime.value) }} /
            {{ formatDuration(player.duration.value) }}</span
          >
        </span>
        <UiIconButton
          v-if="showLyrics"
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
        <!-- The slider is what gives when the row is tight, so the time
             next to it never has to. -->
        <VolumeControl class="hidden min-w-0 lg:flex" width="w-20 min-w-8" />
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
import { useMediaQuery } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import LikeButton from '../player/LikeButton.vue'
import SliderBar from '../player/SliderBar.vue'
import { useSmoothTime } from '../player/useSmoothTime'
import VolumeControl from '../player/VolumeControl.vue'
import { usePlayer } from '/src/model/player'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useNowPlaying } from '/src/model/ui'
import { formatDuration, widestClock } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { showLyrics } = usePlayerPrefs()
const nowPlaying = useNowPlaying()
const { t } = useI18n()
const scrub = ref(null)

const track = computed(() => player.currentTrack.value)

// The phone hairline glides like the desktop scrubber (only animated
// while it's the one on screen).
const isPhone = useMediaQuery('(max-width: 767px)')
const smoothTime = useSmoothTime(
  () => player.currentTime.value,
  () => isPhone.value && player.isPlaying.value,
  () => player.duration.value || 0
)
const smoothPercent = computed(() =>
  isPhone.value && player.duration.value
    ? Math.min(100, (smoothTime.value / player.duration.value) * 100)
    : player.progressPct.value
)

const clockSizer = computed(() => widestClock(player.duration.value))

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
