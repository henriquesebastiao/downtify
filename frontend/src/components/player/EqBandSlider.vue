<template>
  <div class="flex min-w-0 flex-col items-center gap-2 select-none">
    <span
      class="tabular h-4 text-[11px] leading-4 font-semibold transition-opacity"
      :class="
        dragging || modelValue !== 0
          ? 'text-white/85'
          : 'text-white/0 group-hover/eq:text-white/35'
      "
      aria-hidden="true"
      >{{ shortValue }}</span
    >
    <div
      ref="track"
      role="slider"
      tabindex="0"
      aria-orientation="vertical"
      :aria-label="label"
      :aria-valuemin="-limit"
      :aria-valuemax="limit"
      :aria-valuenow="modelValue"
      :aria-valuetext="formatGain(modelValue)"
      class="group relative flex w-9 cursor-pointer touch-none justify-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-white/80"
      :style="{ height: `${height}px` }"
      @pointerdown="onDown"
      @keydown="onKey"
      @dblclick="reset"
    >
      <!-- Track -->
      <span
        class="absolute inset-y-0 w-1.5 rounded-full bg-white/15"
        aria-hidden="true"
      />
      <!-- 0 dB mark -->
      <span
        class="absolute top-1/2 h-px w-4 -translate-y-1/2 bg-white/35"
        aria-hidden="true"
      />
      <!-- Fill from 0 dB to the value -->
      <span
        class="absolute w-1.5 rounded-full"
        :style="fillStyle"
        aria-hidden="true"
      />
      <span
        class="absolute size-4 -translate-y-1/2 rounded-full bg-white shadow-[0_2px_8px_rgb(0_0_0/0.4)] transition-transform duration-150"
        :class="dragging ? 'scale-125' : 'group-hover:scale-110'"
        :style="{ top: `${100 - percent}%` }"
        aria-hidden="true"
      />
    </div>
    <span
      class="tabular text-[11px] font-medium whitespace-nowrap text-white/60"
      aria-hidden="true"
      >{{ caption }}</span
    >
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSlider } from './useSlider'
import { formatGain, GAIN_STEP } from '/src/lib/equalizer'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  limit: { type: Number, required: true },
  label: { type: String, required: true },
  caption: { type: String, required: true },
  color: { type: String, default: '#ffffff' },
  height: { type: Number, default: 180 },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const { track, dragging, percent, onDown, onKey } = useSlider(
  {
    get modelValue() {
      return props.modelValue
    },
    get min() {
      return -props.limit
    },
    get max() {
      return props.limit
    },
    step: GAIN_STEP,
  },
  emit,
  { vertical: true, snap: true }
)

const shortValue = computed(() => {
  const v = Math.round(props.modelValue * 10) / 10
  return v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0'
})

const fillStyle = computed(() => {
  const top = Math.min(50, 100 - percent.value)
  const bottom = Math.min(50, percent.value)
  return {
    top: `${top}%`,
    bottom: `${bottom}%`,
    backgroundColor: props.color,
  }
})

function reset() {
  emit('update:modelValue', 0)
  emit('commit', 0)
}
</script>
