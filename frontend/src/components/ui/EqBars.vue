<template>
  <span
    class="inline-flex items-end gap-0.5"
    :style="{ height: `${size}px` }"
    aria-hidden="true"
  >
    <span
      v-for="n in 3"
      :key="n"
      class="block w-[3px] origin-bottom rounded-[1px] bg-accent"
      :class="playing ? 'animate-eq' : 'scale-y-[0.35]'"
      :style="{ height: `${size}px`, animationDelay: `${-0.3 * (n - 1)}s` }"
    />
  </span>
</template>

<script setup>
defineProps({
  size: { type: Number, default: 14 },
  playing: { type: Boolean, default: true },
})
</script>
