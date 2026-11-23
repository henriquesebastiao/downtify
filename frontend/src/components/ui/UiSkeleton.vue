<template>
  <!-- The shape of what is loading (styles/motion.css → .skeleton): it
       appears only if the wait lasts, and a sheen sweeps across it. Give
       it the size and corners of the thing it stands for. -->
  <div
    class="skeleton rounded-control"
    :class="glass ? 'skeleton-glass' : ''"
    aria-hidden="true"
  />
</template>

<script setup>
defineProps({
  // On the dark Now playing screen instead of the page's surface.
  glass: { type: Boolean, default: false },
})
</script>
