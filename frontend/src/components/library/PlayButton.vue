<template>
  <button
    type="button"
    class="flex size-14 shrink-0 items-center justify-center rounded-full bg-accent text-on-accent shadow-[0_10px_30px_color-mix(in_srgb,var(--c-accent)_35%,transparent)] transition-transform hover:scale-105 active:scale-95 disabled:opacity-50"
    :aria-label="playing ? t('player.pause') : label"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <AppIcon :name="playing ? 'pause' : 'play'" :size="20" />
  </button>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import { useI18n } from '/src/i18n'

defineProps({
  label: { type: String, default: '' },
  playing: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
defineEmits(['click'])
const { t } = useI18n()
</script>
