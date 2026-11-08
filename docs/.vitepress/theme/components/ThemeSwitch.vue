<template>
  <div
    role="radiogroup"
    :aria-label="ui.colorTheme"
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
import { computed } from 'vue'
import Icon from './Icon.vue'
import { useThemeMode } from '../composables/theme-mode'
import { useUi } from '../composables/ui'

defineProps({ labels: { type: Boolean, default: false } })

const { mode, setMode } = useThemeMode()
const { ui } = useUi()
const options = computed(() => [
  { value: 'light', label: ui.value.themeLight, icon: 'sun' },
  { value: 'dark', label: ui.value.themeDark, icon: 'moon' },
  { value: 'system', label: ui.value.themeSystem, icon: 'monitor' },
])
</script>
