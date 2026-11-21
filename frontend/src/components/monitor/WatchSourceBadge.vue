<template>
  <UiBadge v-if="source === 'youtube_music'" tone="neutral" icon="youtube"
    >YouTube Music</UiBadge
  >
  <UiBadge v-else-if="source === 'deezer'" tone="neutral" icon="deezer"
    >Deezer</UiBadge
  >
  <span v-else class="inline-flex flex-wrap items-center gap-1.5">
    <UiBadge tone="spotify" icon="spotify">Spotify</UiBadge>
    <!-- A mix made for one listener: the watch follows the signed-out
         version (see lib/spotifyMix.js). -->
    <UiBadge
      v-if="personalMix"
      tone="warn"
      icon="alert"
      :title="`${t('monitor.personalMixTitle')}. ${t('monitor.personalMixBody')}`"
      >{{ t('monitor.personalMixBadge') }}</UiBadge
    >
  </span>
</template>

<script setup>
import { computed } from 'vue'
import UiBadge from '../ui/UiBadge.vue'
import { isPersonalMix } from '/src/lib/spotifyMix'
import { useI18n } from '/src/i18n'

const props = defineProps({
  source: { type: String, default: 'spotify' },
  // The watch's link, to flag a Spotify mix made for one listener.
  url: { type: String, default: '' },
})
const { t } = useI18n()
const personalMix = computed(() => isPersonalMix(props.url))
</script>
