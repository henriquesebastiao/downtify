<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :fill="icon.filled ? 'currentColor' : 'none'"
    :stroke="icon.filled ? 'none' : 'currentColor'"
    :stroke-width="icon.filled ? undefined : strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    aria-hidden="true"
    v-html="icon.body"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useData } from 'vitepress'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.8 },
})

const { theme } = useData()
const icon = computed(
  () => theme.value.icons[props.name] || theme.value.icons['file-text']
)
</script>
