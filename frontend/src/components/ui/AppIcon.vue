<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    :stroke="filled ? 'none' : 'currentColor'"
    :stroke-width="filled ? undefined : strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    aria-hidden="true"
    v-html="body"
  />
</template>

<script setup>
import { computed } from 'vue'
import { FILLED, STROKE } from './icons'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.8 },
})

// A stroke drawing wins when a name exists in both sets; FILLED is for
// shapes that only read as solids (transport controls, brand marks).
const filled = computed(() => !(props.name in STROKE) && props.name in FILLED)
const body = computed(
  () => STROKE[props.name] || FILLED[props.name] || STROKE.music
)
</script>
