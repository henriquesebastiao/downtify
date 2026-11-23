<template>
  <div class="flex flex-wrap gap-2" role="group" :aria-label="label">
    <button
      v-for="format in formats"
      :key="format"
      type="button"
      class="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium transition-colors disabled:opacity-40"
      :class="
        modelValue.includes(format)
          ? 'bg-fg text-bg'
          : 'bg-surface-2 text-fg-3 hover:bg-raised'
      "
      :aria-pressed="modelValue.includes(format)"
      :disabled="disabled || locked.includes(format)"
      :title="locked.includes(format) ? lockedHint : ''"
      @click="toggle(format)"
    >
      <AppIcon v-if="modelValue.includes(format)" name="check" :size="14" />
      {{ formatLabel(format) }}
    </button>
  </div>
</template>

<script setup>
// Formats picked from FORMATS (downtify/audio_formats.py), as toggles:
// "Formats to avoid" in Settings and the Doctor's "Formats to convert".
import AppIcon from '/src/components/ui/AppIcon.vue'
import { FORMATS, formatLabel } from '/src/lib/audioFormats'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  // Formats that can't be picked (the Downloads format, for "avoid").
  locked: { type: Array, default: () => [] },
  lockedHint: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const formats = FORMATS

function toggle(format) {
  const on = props.modelValue.includes(format)
  const next = on
    ? props.modelValue.filter((f) => f !== format)
    : [...props.modelValue, format]
  emit(
    'update:modelValue',
    FORMATS.filter((f) => next.includes(f))
  )
}
</script>
