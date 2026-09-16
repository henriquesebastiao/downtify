<template>
  <div class="flex gap-2 overflow-x-auto [scrollbar-width:none]">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium whitespace-nowrap transition-colors"
      :class="
        item.id === modelValue
          ? 'bg-fg text-bg'
          : 'bg-surface-2 text-fg-3 hover:bg-raised'
      "
      :aria-pressed="item.id === modelValue"
      @click="$emit('update:modelValue', item.id)"
    >
      {{ item.label }}
      <span
        v-if="item.count !== undefined && item.count !== null"
        class="tabular opacity-60"
        >{{ item.count }}</span
      >
    </button>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
