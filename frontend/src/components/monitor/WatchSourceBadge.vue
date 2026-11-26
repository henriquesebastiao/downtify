<template>
  <UiBadge v-if="source === 'youtube_music'" tone="neutral" icon="youtube"
    >YouTube Music</UiBadge
  >
  <UiBadge v-else-if="source === 'deezer'" tone="neutral" icon="deezer"
    >Deezer</UiBadge
  >
  <UiBadge v-else-if="source === 'musicbrainz'" tone="neutral"
    >MusicBrainz</UiBadge
  >
  <span v-else class="inline-flex flex-wrap items-center gap-1.5">
    <UiBadge tone="spotify" icon="spotify">Spotify</UiBadge>
    <!-- A mix made for one listener: without the Spotify companion the
         watch follows the signed-out version (see lib/spotifyMix.js);
         with it, your own version, or it waits (lib/spotifyCompanion.js). -->
    <UiBadge
      v-if="personalMix && companion.enabled && companion.status === 'ready'"
      tone="accent"
      icon="spotify"
      :title="t('companion.badgeYoursHint')"
      >{{ t('companion.badgeYours') }}</UiBadge
    >
    <UiBadge
      v-else-if="personalMix && companion.enabled"
      tone="warn"
      icon="alert"
      :title="t('companion.badgeHeldHint')"
      >{{ t('companion.badgeHeld') }}</UiBadge
    >
    <UiBadge
      v-else-if="personalMix"
      tone="warn"
      icon="alert"
      :title="`${t('monitor.personalMixTitle')}. ${t('monitor.personalMixBody')}`"
      >{{ t('monitor.personalMixBadge') }}</UiBadge
    >
  </span>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import UiBadge from '../ui/UiBadge.vue'
import { isPersonalMix } from '/src/lib/spotifyMix'
import { useCompanionWatches } from '/src/lib/spotifyCompanion'
import { useI18n } from '/src/i18n'

const props = defineProps({
  source: { type: String, default: 'spotify' },
  // The watch's link, to flag a Spotify mix made for one listener.
  url: { type: String, default: '' },
})
const { t } = useI18n()
const personalMix = computed(() => isPersonalMix(props.url))
// Asked for (again) whenever a badge for a personal mix appears.
const shared = ref(null)
onMounted(() => {
  if (personalMix.value) shared.value = useCompanionWatches()
})
const companion = computed(
  () => shared.value?.value || { enabled: false, status: 'off' }
)
</script>
