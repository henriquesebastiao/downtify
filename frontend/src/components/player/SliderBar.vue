<template>
  <div
    ref="track"
    role="slider"
    tabindex="0"
    :aria-label="label"
    :aria-valuemin="0"
    :aria-valuemax="max"
    :aria-valuenow="Math.round(modelValue)"
    :aria-valuetext="valueText"
    class="group relative flex cursor-pointer touch-none items-center outline-none"
    :style="{ height: `${hitHeight}px` }"
    @pointerdown="onDown"
    @keydown="onKey"
  >
    <div
      class="relative w-full overflow-hidden rounded-full transition-[height] duration-150"
      :class="[
        trackClass,
        dragging ? 'h-1.5' : thin ? 'h-1 group-hover:h-1.5' : 'h-1.5',
      ]"
    >
      <div
        class="absolute inset-y-0 left-0 rounded-full"
        :class="fillClass"
        :style="{ width: `${percent}%` }"
      />
    </div>
    <span
      class="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full shadow transition-opacity group-focus-visible:opacity-100"
      :class="[
        thumbClass,
        dragging || alwaysThumb
          ? 'opacity-100'
          : 'opacity-0 group-hover:opacity-100',
      ]"
      :style="{ left: `${percent}%` }"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSlider } from './useSlider'
import { useSmoothTime } from './useSmoothTime'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 5 },
  label: { type: String, default: '' },
  valueText: { type: String, default: undefined },
  thin: { type: Boolean, default: true },
  alwaysThumb: { type: Boolean, default: false },
  hitHeight: { type: Number, default: 20 },
  trackClass: { type: String, default: 'bg-raised' },
  fillClass: { type: String, default: 'bg-fg group-hover:bg-accent' },
  thumbClass: { type: String, default: 'bg-fg' },
  // For playback progress: glide between time updates while true.
  playing: { type: Boolean, default: undefined },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const {
  track,
  dragging,
  percent: rawPercent,
  onDown,
  onKey,
} = useSlider(props, emit)

const smooth =
  props.playing === undefined
    ? null
    : useSmoothTime(
        () => props.modelValue,
        () => !!props.playing && !dragging.value,
        () => props.max
      )
const percent = computed(() =>
  smooth && !dragging.value && props.max > 0
    ? Math.min(100, (smooth.value / props.max) * 100)
    : rawPercent.value
)
</script>
