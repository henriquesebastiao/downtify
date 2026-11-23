<template>
  <div
    class="relative w-full overflow-hidden rounded-full"
    :class="[track || 'bg-raised']"
    :style="{ height: `${height}px` }"
    role="progressbar"
    :aria-valuenow="indeterminate ? undefined : Math.round(clamped)"
    aria-valuemin="0"
    aria-valuemax="100"
  >
    <div
      v-if="indeterminate"
      class="progress-indeterminate"
      :class="color || 'bg-accent'"
    />
    <!-- Full width, slid back by what is left: moving it is a transform,
         and its rounded end keeps its shape at every value. -->
    <div
      v-else
      class="h-full w-full rounded-full transition-transform duration-(--dur-slow) ease-out-soft"
      :class="color || 'bg-accent'"
      :style="{ transform: `translateX(${clamped - 100}%)` }"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  indeterminate: { type: Boolean, default: false },
  height: { type: Number, default: 4 },
  color: { type: String, default: '' },
  track: { type: String, default: '' },
})

const clamped = computed(() => Math.max(0, Math.min(100, props.value || 0)))
</script>
