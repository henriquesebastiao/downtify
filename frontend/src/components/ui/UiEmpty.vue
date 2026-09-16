<template>
  <div
    class="flex flex-col items-center justify-center gap-3 rounded-panel border border-dashed border-line-3 px-6 py-14 text-center"
  >
    <span
      class="flex size-14 items-center justify-center rounded-full bg-surface-2 text-muted"
    >
      <AppIcon :name="icon" :size="24" />
    </span>
    <div class="flex max-w-sm flex-col gap-1">
      <p class="text-display text-lg font-semibold text-fg">{{ title }}</p>
      <p v-if="body" class="text-sm text-pretty text-muted">{{ body }}</p>
    </div>
    <div v-if="$slots.default" class="mt-2 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'music' },
  title: { type: String, required: true },
  body: { type: String, default: '' },
})
</script>
