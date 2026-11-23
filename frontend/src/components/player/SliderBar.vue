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
    <!-- Thin at rest, fuller under the pointer: a scale, not a height. The
         fill slides along it instead of being resized. -->
    <div
      class="relative h-1.5 w-full overflow-hidden rounded-full transition-transform duration-(--dur-fast) ease-out-soft"
      :class="[
        trackClass,
        thin && !dragging ? 'scale-y-[0.67] group-hover:scale-y-100' : '',
      ]"
    >
      <div
        class="absolute inset-0 rounded-full"
        :class="fillClass"
        :style="{ transform: `translateX(${percent - 100}%)` }"
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
