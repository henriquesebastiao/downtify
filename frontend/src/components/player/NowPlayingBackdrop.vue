<template>
  <!-- The artwork, blown up and blurred. Clipped, or what sticks out lets
       the whole view scroll. -->
  <div
    ref="root"
    class="pointer-events-none absolute inset-0 overflow-hidden"
    aria-hidden="true"
  >
    <div
      class="absolute inset-0 transition-colors duration-700"
      :style="{ backgroundColor: tint }"
    />
    <img
      v-if="track?.hasCover"
      :src="track.cover"
      alt=""
      class="absolute inset-0 size-full scale-125 object-cover opacity-55 blur-[90px] saturate-150"
    />
    <!-- The song's music video (issue #680): the whole background, muted
         and in step with the song, faded in once it can play, under a
         dark veil so the cover and the lyrics stay readable. -->
    <template v-if="video">
      <!-- Covers the whole view, never letterboxed: the frame itself is
           cropped like a cover image, and black bars burnt into the
           picture (measured on the server) are zoomed out of view. -->
      <MusicVideo
        :key="video"
        :src="video"
        :player="player"
        class="absolute max-w-none transition-opacity duration-(--dur-sheet) ease-out-soft"
        :class="[
          videoReady ? 'opacity-100' : 'opacity-0',
          placement ? '' : 'inset-0 object-cover',
        ]"
        :style="placementStyle"
        @ready="videoReady = true"
        @failed="onFailed"
      />
      <div
        class="absolute inset-0 bg-black/55 transition-opacity duration-(--dur-sheet) ease-out-soft"
        :class="videoReady ? 'opacity-100' : 'opacity-0'"
      />
    </template>
    <div
      class="absolute inset-0 bg-gradient-to-b from-black/25 via-black/45 to-black/80"
    />
    <Transition name="fade">
      <KaraokeSmoke v-if="karaoke" :palette="palette" :playing="playing" />
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useElementSize } from '@vueuse/core'
import KaraokeSmoke from './KaraokeSmoke.vue'
import MusicVideo from './MusicVideo.vue'
import { coverPicture } from '/src/lib/musicVideo'
import { hueFor } from '/src/lib/format'

const props = defineProps({
  track: { type: Object, default: null },
  palette: { type: Object, default: null },
  karaoke: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  // The playing song's music video URL ('' for none), and the player it
  // follows (model/player.js).
  video: { type: String, default: '' },
  player: { type: Object, default: null },
  // Black bars burnt into the video's picture (GET /api/music-video).
  crop: { type: Object, default: null },
})
const emit = defineEmits(['video-failed'])

const videoReady = ref(false)
const root = ref(null)
const { width: boxWidth, height: boxHeight } = useElementSize(root)
const placement = computed(() =>
  coverPicture(props.crop, boxWidth.value, boxHeight.value)
)
const placementStyle = computed(() => {
  const box = placement.value
  if (!box) return undefined
  return {
    left: `${box.left}px`,
    top: `${box.top}px`,
    width: `${box.width}px`,
    height: `${box.height}px`,
  }
})
watch(
  () => props.video,
  () => {
    videoReady.value = false
  }
)
function onFailed() {
  videoReady.value = false
  emit('video-failed')
}

const tint = computed(
  () =>
    props.palette?.background ||
    `oklch(0.3 0.06 ${hueFor(props.track?.album || props.track?.title)})`
)
</script>
