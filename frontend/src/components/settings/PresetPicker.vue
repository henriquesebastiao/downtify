<template>
  <div class="flex flex-wrap items-center gap-2">
    <div class="flex flex-wrap gap-1.5">
      <button
        v-for="preset in presets"
        :key="preset"
        type="button"
        class="tabular h-9 min-w-11 rounded-control border px-3 text-[13px] font-semibold transition-colors"
        :class="
          preset === modelValue
            ? 'border-accent/50 bg-accent/12 text-accent'
            : 'border-line-2 text-fg-3 hover:border-line-3 hover:bg-surface-2'
        "
        :aria-pressed="preset === modelValue"
        @click="$emit('update:modelValue', preset)"
      >
        {{ format ? format(preset) : preset }}
      </button>
    </div>
    <label
      class="flex h-9 items-center gap-1.5 rounded-control border border-line-2 px-2.5 focus-within:border-accent"
      :title="customLabel"
    >
      <span class="sr-only">{{ customLabel }}</span>
      <input
        type="number"
        inputmode="numeric"
        :min="min"
        :max="max"
        :value="modelValue"
        class="tabular w-14 bg-transparent text-[13px] outline-none"
        @change="onChange"
      />
      <span v-if="unit" class="text-xs text-faint">{{ unit }}</span>
    </label>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Number, default: 0 },
  presets: { type: Array, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: '' },
  customLabel: { type: String, default: '' },
  format: { type: Function, default: null },
})
const emit = defineEmits(['update:modelValue'])

function onChange(event) {
  const value = Number.parseInt(event.target.value, 10)
  const clamped = Number.isNaN(value)
    ? props.min
    : Math.min(props.max, Math.max(props.min, value))
  event.target.value = clamped
  emit('update:modelValue', clamped)
}
</script>
