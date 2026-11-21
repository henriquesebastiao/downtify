<template>
  <div class="max-w-60 min-w-0 text-right">
    <p class="eyebrow !text-white/55">
      {{ t('player.upNext') }}
    </p>
    <p class="truncate text-sm font-medium text-white/85">
      {{ track.title }}
      <span v-if="track.artist" class="text-white/55"
        >· {{ track.artist }}</span
      >
    </p>
  </div>
</template>

<script setup>
import { useI18n } from '/src/i18n'

defineProps({
  track: { type: Object, required: true },
})

const { t } = useI18n()
</script>
