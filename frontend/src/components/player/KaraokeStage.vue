<template>
  <div
    class="fixed inset-0 overflow-hidden bg-[#07080b] text-white"
    :class="{ 'cursor-none': idle }"
  >
    <NowPlayingBackdrop
      :track="track"
      :palette="palette"
      :playing="isPlaying"
      karaoke
    />

    <div
      v-if="track"
      class="relative flex h-full flex-col px-5 pt-3 pb-2 lg:px-10"
    >
      <header class="flex h-12 shrink-0 items-center gap-3">
        <CoverArt
          :src="track.hasCover ? track.cover : ''"
          :name="track.album || track.title"
          rounded="rounded-[9px]"
          :letter-size="18"
          :icon-size="20"
          class="size-11 shrink-0"
        />
        <div class="min-w-0 flex-1">
          <h1 class="text-display truncate text-[15px] leading-tight font-bold">
            {{ track.title }}
          </h1>
          <p class="mt-0.5 truncate text-[13px] leading-tight text-white/70">
            {{ track.artist }}
          </p>
        </div>
        <KaraokeUpNext
          v-if="nextTrack"
          :track="nextTrack"
          class="hidden md:block"
        />
      </header>
      <div class="min-h-0 flex-1 py-1">
        <LyricsPanel :player="mirror" karaoke readonly />
      </div>
    </div>

    <div
      v-else
      class="relative flex h-full flex-col items-center justify-center gap-4 px-5 text-center"
    >
      <AppIcon name="mic-vocal" :size="48" class="text-white/35" />
      <p class="text-lg text-white/70">{{ t('player.karaokeWaiting') }}</p>
    </div>

    <!-- Not a playback control: out of the way, and of the picture, once
         the mouse stops. -->
    <button
      v-if="canFullscreen"
      type="button"
      class="absolute right-4 bottom-4 flex size-10 items-center justify-center rounded-full bg-white/10 transition-opacity hover:bg-white/20"
      :class="idle ? 'opacity-0' : 'opacity-100'"
      :aria-label="t('player.fullscreen')"
      :aria-pressed="isFullscreen"
      :title="t('player.fullscreen')"
      @click="toggleFullscreen()"
    >
      <AppIcon name="expand" :size="20" />
    </button>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useFullscreen, useIdle, useWakeLock } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import KaraokeUpNext from './KaraokeUpNext.vue'
import LyricsPanel from './LyricsPanel.vue'
import NowPlayingBackdrop from './NowPlayingBackdrop.vue'
import { connectToHost } from '/src/model/karaokeStageMirror'
import { useCoverPalette } from '/src/model/coverPalette'
import { useI18n } from '/src/i18n'

const IDLE_MS = 3000

const { t } = useI18n()
const mirror = connectToHost(
  new URLSearchParams(window.location.search).get('host') || ''
)
const track = mirror.currentTrack
const nextTrack = mirror.nextTrack
const isPlaying = mirror.isPlaying
const palette = useCoverPalette(track)

const { idle } = useIdle(IDLE_MS)
const {
  isSupported: canFullscreen,
  isFullscreen,
  toggle: toggleFullscreen,
} = useFullscreen()

// Only audio plays in the other window, which doesn't keep a screen awake.
const { request: keepScreenAwake } = useWakeLock()
onMounted(() => {
  keepScreenAwake('screen').catch(() => {})
})
onBeforeUnmount(mirror.stop)
</script>
