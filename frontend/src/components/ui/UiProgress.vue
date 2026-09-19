<template>
  <div
    class="relative w-full overflow-hidden rounded-full"
    :class="[track || 'bg-raised']"
    :style="{ height: `${height}px` }"
    role="progressbar"
    :aria-valuenow="indeterminate ? undefined : Math.round(value)"
    aria-valuemin="0"
    aria-valuemax="100"
  >
    <div v-if="indeterminate" class="shimmer absolute inset-0" />
    <div
      v-else
      class="h-full rounded-full transition-[width] duration-300 ease-out"
      :class="color || 'bg-accent'"
      :style="{ width: `${Math.max(0, Math.min(100, value))}%` }"
    />
  </div>
</template>

<script setup>
defineProps({
  value: { type: Number, default: 0 },
  indeterminate: { type: Boolean, default: false },
  height: { type: Number, default: 4 },
  color: { type: String, default: '' },
  track: { type: String, default: '' },
})
</script>
