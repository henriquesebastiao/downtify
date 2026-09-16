<template>
  <label
    class="relative inline-flex shrink-0 items-center rounded-control border border-line-2 bg-transparent text-fg-3 transition-colors focus-within:border-accent hover:border-line-3"
    :class="[
      block ? 'w-full' : '',
      size === 'sm' ? 'h-8 text-xs' : 'h-10 text-[13px]',
    ]"
  >
    <AppIcon
      v-if="icon"
      :name="icon"
      :size="15"
      class="pointer-events-none absolute left-3 text-muted"
    />
    <span class="sr-only">{{ label }}</span>
    <select
      :value="modelValue"
      class="h-full w-full cursor-pointer appearance-none bg-transparent pr-9 outline-none"
      :class="icon ? 'pl-9' : 'pl-3.5'"
      @change="onChange"
    >
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
        class="bg-surface text-fg"
      >
        {{ option.label }}
      </option>
    </select>
    <AppIcon
      name="chevron-down"
      :size="14"
      stroke-width="2"
      class="pointer-events-none absolute right-3 text-muted"
    />
  </label>
</template>

<script setup>
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, required: true },
  label: { type: String, default: '' },
  icon: { type: String, default: '' },
  block: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
})
const emit = defineEmits(['update:modelValue'])

function onChange(event) {
  const raw = event.target.value
  const match = props.options.find((option) => String(option.value) === raw)
  emit('update:modelValue', match ? match.value : raw)
}
</script>
