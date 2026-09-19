<template>
  <div
    role="radiogroup"
    aria-label="Color theme"
    class="inline-flex shrink-0 items-center gap-0.5 rounded-control border border-line-2 p-0.5"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="mode === option.value"
      :title="option.label"
      class="flex h-8 items-center gap-1.5 rounded-[7px] px-2 text-xs font-semibold transition-colors"
      :class="
        mode === option.value
          ? 'bg-surface-2 text-fg'
          : 'text-muted hover:text-fg'
      "
      @click="setMode(option.value)"
    >
      <Icon :name="option.icon" :size="15" />
      <span :class="labels ? '' : 'sr-only'">{{ option.label }}</span>
    </button>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'
import { useThemeMode } from '../composables/theme-mode'

defineProps({ labels: { type: Boolean, default: false } })

const { mode, setMode } = useThemeMode()
const options = [
  { value: 'light', label: 'Light', icon: 'sun' },
  { value: 'dark', label: 'Dark', icon: 'moon' },
  { value: 'system', label: 'System', icon: 'monitor' },
]
</script>
