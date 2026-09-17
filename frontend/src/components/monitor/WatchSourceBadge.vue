<template>
  <UiBadge v-if="source === 'youtube_music'" tone="neutral" icon="youtube"
    >YouTube Music</UiBadge
  >
  <UiBadge v-else tone="spotify" icon="spotify">Spotify</UiBadge>
</template>

<script setup>
import UiBadge from '../ui/UiBadge.vue'

defineProps({ source: { type: String, default: 'spotify' } })
</script>
