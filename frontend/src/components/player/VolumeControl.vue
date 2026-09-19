<template>
  <div class="flex items-center gap-2">
    <UiIconButton
      :icon="icon"
      :label="player.isMuted.value ? t('player.unmute') : t('player.mute')"
      size="sm"
      @click="player.toggleMute()"
    />
    <SliderBar
      :model-value="player.isMuted.value ? 0 : player.volume.value * 100"
      :label="t('player.volume')"
      :value-text="`${Math.round(player.volume.value * 100)}%`"
      :step="5"
      :class="width"
      :track-class="trackClass"
      :fill-class="fillClass"
      :thumb-class="thumbClass"
      @update:model-value="(v) => player.setVolume(v / 100)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SliderBar from './SliderBar.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import { usePlayer } from '/src/model/player'
import { useI18n } from '/src/i18n'

defineProps({
  width: { type: String, default: 'w-24' },
  trackClass: { type: String, default: 'bg-raised' },
  fillClass: { type: String, default: 'bg-fg-3 group-hover:bg-accent' },
  thumbClass: { type: String, default: 'bg-fg' },
})

const player = usePlayer()
const { t } = useI18n()

const icon = computed(() => {
  if (player.isMuted.value || player.volume.value === 0) return 'volume-mute'
  return player.volume.value < 0.5 ? 'volume-low' : 'volume'
})
</script>
