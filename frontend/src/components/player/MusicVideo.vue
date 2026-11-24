<template>
  <!-- Muted: the song keeps the sound (equalizer, normalization and
       lyrics all follow it); the picture is kept in step with it. -->
  <video
    ref="video"
    :src="src"
    class="size-full"
    muted
    playsinline
    preload="auto"
    disablepictureinpicture
    :aria-label="label || undefined"
    @loadeddata="onReady"
    @error="emit('failed')"
  />
</template>

<script setup>
// A song's music video in Now playing (issue #680, lib/musicVideo.js).
import { onBeforeUnmount, ref, watch } from 'vue'
import { videoSyncAction } from '/src/lib/musicVideo'

const props = defineProps({
  src: { type: String, required: true },
  // The app's player (model/player.js): its time, state and speed.
  player: { type: Object, required: true },
  label: { type: String, default: '' },
})
const emit = defineEmits(['ready', 'failed'])
const video = ref(null)
let ready = false

function sync() {
  const el = video.value
  if (!el || !ready) return
  el.playbackRate = props.player.playbackRate?.value || 1
  const action = videoSyncAction({
    audioTime: props.player.currentTime.value,
    videoTime: el.currentTime,
    duration: el.duration,
    playing: props.player.isPlaying.value,
    videoPaused: el.paused,
  })
  if (action.seek !== null) el.currentTime = action.seek
  if (action.play) el.play().catch(() => {})
  if (action.pause) el.pause()
}

function onReady() {
  ready = true
  sync()
  emit('ready')
}

watch(
  () => [
    props.player.currentTime.value,
    props.player.isPlaying.value,
    props.player.playbackRate?.value,
  ],
  sync
)
watch(
  () => props.src,
  () => {
    ready = false
  }
)

onBeforeUnmount(() => {
  video.value?.pause()
})
</script>
