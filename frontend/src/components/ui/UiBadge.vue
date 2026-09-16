<template>
  <span
    class="inline-flex h-[22px] shrink-0 items-center gap-1.5 rounded-full border px-2.5 text-[11px] font-semibold whitespace-nowrap"
    :class="toneClass"
  >
    <AppIcon v-if="icon" :name="icon" :size="12" stroke-width="2.4" />
    <slot />
  </span>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  tone: { type: String, default: 'neutral' },
  icon: { type: String, default: '' },
})

const toneClass = computed(
  () =>
    ({
      accent: 'border-transparent bg-accent/12 text-accent',
      warn: 'border-transparent bg-warn/12 text-warn',
      danger: 'border-transparent bg-danger/12 text-danger',
      neutral: 'border-line-3 bg-surface-2 text-muted',
      spotify: 'border-spotify/25 bg-spotify/12 text-spotify',
    })[props.tone]
)
</script>
