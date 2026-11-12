<template>
  <!-- The artwork, blown up and blurred. Clipped, or what sticks out lets
       the whole view scroll. -->
  <div
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
    <div
      class="absolute inset-0 bg-gradient-to-b from-black/25 via-black/45 to-black/80"
    />
    <Transition name="fade">
      <KaraokeSmoke v-if="karaoke" :palette="palette" :playing="playing" />
    </Transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import KaraokeSmoke from './KaraokeSmoke.vue'
import { hueFor } from '/src/lib/format'

const props = defineProps({
  track: { type: Object, default: null },
  palette: { type: Object, default: null },
  karaoke: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
})

const tint = computed(
  () =>
    props.palette?.background ||
    `oklch(0.3 0.06 ${hueFor(props.track?.album || props.track?.title)})`
)
</script>
