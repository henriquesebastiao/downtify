<template>
  <!-- A tall invisible hit strip straddling the player's top edge. At
       rest only the hairline shows; under the pointer (or while
       dragging, or with keyboard focus) the rail swells, a thumb pops
       up and a tooltip shows the time under the cursor. -->
  <div
    role="slider"
    tabindex="0"
    :aria-label="label"
    :aria-valuemin="0"
    :aria-valuemax="Math.round(max)"
    :aria-valuenow="Math.round(modelValue)"
    :aria-valuetext="valueText"
    class="seek-bar absolute inset-x-0 cursor-pointer touch-none outline-none"
    :class="{ 'is-active': active }"
    :style="{ top: `${-hitAbove}px`, height: `${hitAbove + hitBelow}px` }"
    @pointerdown="onDown"
    @pointerenter="onEnter"
    @pointermove="onMove"
    @pointerleave="hovering = false"
    @keydown="onKey"
    @focus="onFocus"
    @blur="focused = false"
  >
    <div
      ref="track"
      class="seek-rail absolute inset-x-4 rounded-full"
      :style="{ top: `${hitAbove + 2}px` }"
    >
      <div
        class="seek-fill absolute inset-y-0 left-0 rounded-full bg-accent"
        :style="{ width: `${percent}%` }"
      />
      <span
        class="seek-thumb absolute top-1/2 size-3 rounded-full bg-accent shadow"
        :style="{ left: `${percent}%` }"
      />
      <span
        v-if="tipShown"
        ref="tip"
        class="tabular pointer-events-none absolute bottom-full mb-2.5 rounded-md bg-raised px-1.5 py-0.5 text-xs whitespace-nowrap text-fg shadow"
        :style="{ left: `${tipLeft}px` }"
        aria-hidden="true"
        >{{ formatDuration(tipTime) }}</span
      >
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useSlider } from './useSlider'
import { useSmoothTime } from './useSmoothTime'
import { formatDuration } from '/src/lib/format'
import { railRatio, tooltipLeft } from '/src/lib/seekHover'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  max: { type: Number, default: 1 },
  step: { type: Number, default: 5 },
  label: { type: String, default: '' },
  valueText: { type: String, default: undefined },
  playing: { type: Boolean, default: false },
  // Hit area above and below the player's top edge.
  hitAbove: { type: Number, default: 14 },
  hitBelow: { type: Number, default: 10 },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const {
  track,
  dragging,
  percent: rawPercent,
  onDown,
  onKey,
} = useSlider(props, emit)

const smooth = useSmoothTime(
  () => props.modelValue,
  () => props.playing && !dragging.value,
  () => props.max
)
const percent = computed(() =>
  !dragging.value && props.max > 0
    ? Math.min(100, (smooth.value / props.max) * 100)
    : rawPercent.value
)

const hovering = ref(false)
const hoverRatio = ref(0)
const focused = ref(false)
const active = computed(() => hovering.value || dragging.value || focused.value)

function onEnter(event) {
  // Touch has no hover: it grows only while dragging.
  if (event.pointerType === 'touch') return
  hovering.value = true
  onMove(event)
}

function onMove(event) {
  if (event.pointerType === 'touch') return
  hoverRatio.value = railRatio(
    event.clientX,
    track.value?.getBoundingClientRect()
  )
}

function onFocus(event) {
  focused.value = event.target.matches?.(':focus-visible') ?? true
}

// While dragging (or keyboard-focused) the tooltip follows the playhead;
// otherwise it previews the spot under the cursor.
const tipShown = computed(
  () => props.max > 0 && (dragging.value || hovering.value || focused.value)
)
const tipRatio = computed(() =>
  dragging.value || !hovering.value ? percent.value / 100 : hoverRatio.value
)
const tipTime = computed(() => tipRatio.value * props.max)

const tip = ref(null)
const tipWidth = ref(40)
watch(tipShown, async (shown) => {
  if (!shown) return
  await nextTick()
  if (tip.value) tipWidth.value = tip.value.offsetWidth
})
const tipLeft = computed(() =>
  tooltipLeft(tipRatio.value, track.value?.offsetWidth || 0, tipWidth.value, 8)
)
</script>

<style scoped>
.seek-rail {
  height: 2px;
  margin-top: -1px;
  background-color: transparent;
  transition:
    height 160ms cubic-bezier(0.2, 0.9, 0.3, 1.3),
    margin-top 160ms cubic-bezier(0.2, 0.9, 0.3, 1.3),
    background-color 160ms ease;
}

.seek-thumb {
  transform: translate(-50%, -50%) scale(0);
  transition: transform 160ms cubic-bezier(0.2, 0.9, 0.3, 1.3);
}

.is-active .seek-rail {
  height: 6px;
  margin-top: -3px;
  background-color: color-mix(in srgb, var(--color-fg) 22%, transparent);
}

.is-active .seek-thumb {
  transform: translate(-50%, -50%) scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .seek-rail,
  .seek-thumb {
    transition: none;
  }
}
</style>
