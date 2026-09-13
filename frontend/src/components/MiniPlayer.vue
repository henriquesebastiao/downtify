<template>
  <!-- Collapsed: a small floating "now playing" button instead of the
       bar, so the user can still tell something is playing and bring
       the bar back with one tap. -->
  <button
    v-if="showRestoreButton"
    type="button"
    class="surface-strong fixed bottom-4 right-4 z-40 flex h-12 w-12 items-center justify-center rounded-full shadow-glow-sm hover:scale-105 active:scale-95 transition"
    :title="t('player.showBar')"
    @click="collapsed = false"
  >
    <Icon icon="fa6-solid:play" class="h-5 w-5 text-primary" />
  </button>

  <div
    v-if="showBar"
    class="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-base-100/90 backdrop-blur-md"
  >
    <div
      class="mx-auto flex h-16 max-w-6xl items-center gap-2 px-3 sm:gap-3 sm:px-6"
    >
      <!-- Cover — hidden on mobile so the row has room to breathe -->
      <router-link
        :to="{ name: 'Player' }"
        class="relative hidden h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-primary/10 text-primary sm:flex"
        :title="t('player.nowPlaying')"
      >
        <img
          v-if="cover && !coverFailed"
          :src="cover"
          :alt="trackTitle"
          class="absolute inset-0 h-full w-full object-cover"
          @error="coverFailed = true"
        />
        <Icon v-else icon="fa6-solid:music" class="h-5 w-5" />
      </router-link>

      <!-- Title / artist — tap to open the full Player -->
      <router-link
        :to="{ name: 'Player' }"
        class="flex min-w-0 flex-1 flex-col justify-center"
      >
        <MarqueeText :text="trackTitle" class="text-sm font-semibold" />
        <MarqueeText :text="trackArtist" class="text-xs text-base-content/60" />
      </router-link>

      <!-- Transport -->
      <div class="flex shrink-0 items-center gap-0.5 sm:gap-1">
        <button
          class="icon-btn hidden sm:inline-flex"
          :class="{ 'icon-btn-active': player.shuffle.value }"
          @click="player.toggleShuffle()"
          :title="
            player.shuffle.value
              ? t('player.shuffleOn')
              : t('player.shuffleOff')
          "
        >
          <Icon icon="fa6-solid:shuffle" class="h-4 w-4" />
        </button>
        <button
          class="icon-btn"
          @click="player.prev()"
          :title="t('player.previous')"
        >
          <Icon icon="fa6-solid:backward-step" class="h-4 w-4" />
        </button>
        <button
          class="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-content shadow-glow-sm hover:scale-105 active:scale-95 transition"
          @click="player.toggle()"
          :title="player.isPlaying.value ? t('player.pause') : t('player.play')"
        >
          <Icon
            :icon="
              player.isPlaying.value ? 'fa6-solid:pause' : 'fa6-solid:play'
            "
            class="h-4 w-4"
          />
        </button>
        <button
          class="icon-btn"
          @click="player.next()"
          :title="t('player.next')"
        >
          <Icon icon="fa6-solid:forward-step" class="h-4 w-4" />
        </button>
        <button
          class="icon-btn relative hidden sm:inline-flex"
          :class="{ 'icon-btn-active': player.repeatMode.value !== 'off' }"
          @click="player.cycleRepeat()"
          :title="repeatTitle"
        >
          <Icon icon="fa6-solid:arrows-rotate" class="h-4 w-4" />
          <span
            v-if="player.repeatMode.value === 'one'"
            class="absolute -bottom-0.5 -right-0.5 flex h-3.5 min-w-[0.875rem] items-center justify-center rounded-full bg-primary px-0.5 text-[8px] font-bold text-primary-content"
          >
            1
          </span>
        </button>
      </div>

      <!-- Volume + collapse -->
      <div class="flex shrink-0 items-center gap-0.5 sm:gap-1">
        <div ref="volumeWrapperEl" class="relative hidden sm:block">
          <button
            class="icon-btn"
            @click="volumePopoverOpen = !volumePopoverOpen"
            :title="t('player.volume')"
          >
            <Icon :icon="volumeIcon" class="h-4 w-4" />
          </button>
          <div
            v-if="volumePopoverOpen"
            class="surface-strong absolute bottom-full right-0 mb-2 flex items-center gap-2 rounded-full px-4 py-3"
          >
            <button
              class="icon-btn shrink-0"
              @click="player.toggleMute()"
              :title="
                player.isMuted.value ? t('player.unmute') : t('player.mute')
              "
            >
              <Icon :icon="volumeIcon" class="h-4 w-4" />
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              :value="player.isMuted.value ? 0 : player.volume.value"
              @input="onVolume($event)"
              class="player-range w-24"
              :title="t('player.volume')"
            />
          </div>
        </div>
        <button
          class="icon-btn"
          @click="collapsed = true"
          :title="t('player.hideBar')"
        >
          <Icon icon="fa6-solid:chevron-down" class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'

import MarqueeText from './MarqueeText.vue'
import { usePlayer } from '../model/player'
import { useMiniPlayer } from '../model/miniPlayer'
import { useI18n } from '../i18n'

const player = usePlayer()
const { collapsed, showBar, showRestoreButton } = useMiniPlayer()
const { t } = useI18n()

const coverFailed = ref(false)

// A new track may have a cover the old one didn't — don't keep hiding
// it behind a failure that belonged to a different file.
watch(
  () => player.currentTrack.value?.file,
  () => {
    coverFailed.value = false
  }
)

const cover = computed(() => player.currentTrack.value?.cover || '')

const trackTitle = computed(() => {
  const c = player.currentTrack.value
  return c && c.title ? c.title : t('player.empty')
})

const trackArtist = computed(() => {
  const c = player.currentTrack.value
  if (c && c.artist) return c.artist
  if (c) return t('common.unknownArtist')
  return ''
})

const repeatTitle = computed(() => {
  if (player.repeatMode.value === 'one') return t('player.repeatOne')
  if (player.repeatMode.value === 'all') return t('player.repeatAll')
  return t('player.repeatOff')
})

const volumeIcon = computed(() => {
  if (player.isMuted.value || player.volume.value === 0) {
    return 'fa6-solid:volume-xmark'
  }
  return player.volume.value < 0.5
    ? 'fa6-solid:volume-low'
    : 'fa6-solid:volume-high'
})

function onVolume(event) {
  player.setVolume(parseFloat(event.target.value))
}

// Closes the volume popover on any click outside it, same as a native
// <select>/menu would.
const volumeWrapperEl = ref(null)
const volumePopoverOpen = ref(false)

function onDocumentClick(event) {
  if (volumeWrapperEl.value && !volumeWrapperEl.value.contains(event.target)) {
    volumePopoverOpen.value = false
  }
}

watch(volumePopoverOpen, (open) => {
  if (open) {
    document.addEventListener('click', onDocumentClick)
  } else {
    document.removeEventListener('click', onDocumentClick)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>
