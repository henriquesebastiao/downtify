<template>
  <p class="flex items-start gap-2">
    <AppIcon
      :name="ok ? 'check' : 'alert'"
      :size="16"
      class="mt-0.5 shrink-0"
      :class="ok ? 'text-accent' : 'text-warn'"
    />
    <span :class="ok ? 'text-fg-3' : 'text-warn'">{{ text }}</span>
  </p>
</template>

<script setup>
import AppIcon from '/src/components/ui/AppIcon.vue'

defineProps({
  ok: { type: Boolean, default: false },
  text: { type: String, required: true },
})
</script>
