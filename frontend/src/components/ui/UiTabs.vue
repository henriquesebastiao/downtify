<template>
  <div
    role="tablist"
    class="-mb-px flex gap-6 overflow-x-auto border-b border-line [scrollbar-width:none] sm:gap-7"
  >
    <component
      :is="item.to ? RouterLink : 'button'"
      v-for="item in items"
      :key="item.id"
      :to="item.to || undefined"
      :type="item.to ? undefined : 'button'"
      role="tab"
      :aria-selected="item.id === modelValue"
      class="relative shrink-0 whitespace-nowrap pb-3 text-sm transition-colors"
      :class="
        item.id === modelValue
          ? 'font-semibold text-fg'
          : 'font-medium text-muted hover:text-fg-3'
      "
      @click="$emit('update:modelValue', item.id)"
    >
      {{ item.label }}
      <span
        v-if="item.count !== undefined && item.count !== null"
        class="tabular ml-1 font-medium text-faint"
        >{{ item.count }}</span
      >
      <span
        v-if="item.id === modelValue"
        class="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-accent"
      />
    </component>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
