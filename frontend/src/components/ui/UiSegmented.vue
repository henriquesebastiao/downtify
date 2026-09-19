<template>
  <div
    class="inline-flex h-10 shrink-0 gap-0.5 rounded-control border border-line-2 bg-surface p-[3px]"
    role="radiogroup"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="option.value === modelValue"
      :title="option.label"
      :aria-label="option.label"
      class="flex min-w-9 items-center justify-center gap-1.5 rounded-[7px] px-2 text-[13px] font-medium transition-colors"
      :class="
        option.value === modelValue
          ? 'bg-raised text-fg'
          : 'text-faint hover:text-fg-3'
      "
      @click="$emit('update:modelValue', option.value)"
    >
      <AppIcon v-if="option.icon" :name="option.icon" :size="16" />
      <span v-if="showLabels">{{ option.label }}</span>
    </button>
  </div>
</template>

<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  options: { type: Array, required: true },
  modelValue: { type: [String, Number], default: '' },
  showLabels: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>
