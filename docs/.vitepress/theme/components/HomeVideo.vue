<template>
  <figure class="relative w-full max-w-[1040px]">
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -inset-x-6 -inset-y-6 rounded-[40px] bg-[radial-gradient(50%_50%_at_50%_50%,color-mix(in_srgb,var(--c-accent)_20%,transparent),transparent_72%)] blur-2xl"
    />
    <div
      class="relative overflow-hidden rounded-[18px] border border-line-3 bg-black shadow-[0_30px_80px_-24px_rgb(0_0_0/0.6)]"
    >
      <video
        ref="player"
        class="block aspect-video w-full cursor-pointer"
        :poster="withBase(video.poster)"
        :aria-label="video.label"
        muted
        playsinline
        loop
        preload="metadata"
        @click="toggle"
        @play="playing = true"
        @pause="playing = false"
      >
        <source :src="withBase(video.src)" type="video/mp4" />
      </video>
      <button
        type="button"
        class="absolute bottom-3 left-3 flex size-10 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur-sm transition-colors hover:bg-black/75"
        :aria-label="playing ? ui.pauseVideo : ui.playVideo"
        :title="playing ? ui.pauseVideo : ui.playVideo"
        @click="toggle"
      >
        <Icon :name="playing ? 'pause' : 'play'" :size="17" />
      </button>
    </div>
    <figcaption class="sr-only">{{ video.label }}</figcaption>
  </figure>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'
import Icon from './Icon.vue'
import { useUi } from '../composables/ui'

// The demo reel: plays muted while it's on screen, unless the reader asked
// for reduced motion or paused it. It has no sound track.
defineProps({ video: { type: Object, required: true } })

const { ui } = useUi()
const player = ref(null)
const playing = ref(false)
let pausedByReader = false
let observer = null

function play() {
  player.value?.play()?.catch(() => {
    // Autoplay refused: the poster and the play button stay.
  })
}

function toggle() {
  if (!player.value) return
  if (player.value.paused) {
    pausedByReader = false
    play()
  } else {
    pausedByReader = true
    player.value.pause()
  }
}

onMounted(() => {
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches
  if (still || !('IntersectionObserver' in window)) return
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        if (!pausedByReader) play()
      } else {
        player.value?.pause()
      }
    },
    { threshold: 0.15 }
  )
  observer.observe(player.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>
