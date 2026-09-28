<template>
  <UiBadge
    tone="warn"
    icon="wand"
    tabindex="0"
    role="note"
    :title="t('settings.experimentalHint')"
    :aria-label="`${t('settings.experimental')}: ${t('settings.experimentalHint')}`"
  >
    {{ t('settings.experimental') }}
  </UiBadge>
</template>

<script setup>
// Marks a feature that is still being built. Hovering it - or focusing it
// with the keyboard - explains what that means for the user; the badge
// alone only says "experimental".
import UiBadge from './UiBadge.vue'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
</script>
