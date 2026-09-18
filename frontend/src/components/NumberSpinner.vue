<template>
  <div class="inline-flex items-center gap-1.5">
    <button
      type="button"
      class="btn btn-ghost btn-xs btn-circle rounded-full"
      :disabled="disabled || modelValue <= min"
      @click="setValue(modelValue - 1)"
    >
      <Icon icon="fa6-solid:minus" class="h-3 w-3" />
    </button>
    <input
      type="number"
      inputmode="numeric"
      :min="min"
      :max="max"
      :disabled="disabled"
      class="spinner-input input input-sm w-14 text-center rounded-xl bg-base-100/85 border border-white/10 focus:border-primary/60"
      :value="modelValue"
      @change="onInputChange"
    />
    <button
      type="button"
      class="btn btn-ghost btn-xs btn-circle rounded-full"
      :disabled="disabled || modelValue >= max"
      @click="setValue(modelValue + 1)"
    >
      <Icon icon="fa6-solid:plus" class="h-3 w-3" />
    </button>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

import { clampSpinnerValue } from '../model/numberSpinner'

const props = defineProps({
  modelValue: { type: Number, required: true },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 10 },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

function clamp(value) {
  return clampSpinnerValue(value, props.min, props.max)
}

function setValue(value) {
  const clamped = clamp(value)
  if (clamped !== props.modelValue) emit('update:modelValue', clamped)
}

function onInputChange(event) {
  const parsed = parseInt(event.target.value, 10)
  const clamped = clamp(Number.isNaN(parsed) ? props.min : parsed)
  setValue(clamped)
  // The input isn't a v-model, so out-of-range/non-numeric text the user
  // typed must be corrected here explicitly rather than relying on the
  // modelValue prop round-trip, which is a no-op (no re-render) when the
  // clamped value happens to match what the prop already was.
  event.target.value = clamped
}
</script>

<style scoped>
/* The +/- buttons already provide stepping, so the browser's own
   up/down spinner (rendered inside the input, doubling up with the
   custom buttons) is hidden here rather than styled to match. */
.spinner-input::-webkit-inner-spin-button,
.spinner-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.spinner-input {
  -moz-appearance: textfield;
  appearance: textfield;
}
</style>
