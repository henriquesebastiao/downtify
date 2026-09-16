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
import { computed, ref } from 'vue'

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
})
const emit = defineEmits(['update:modelValue', 'commit'])

const track = ref(null)
const dragging = ref(false)
const dragValue = ref(0)

const shown = computed(() =>
  dragging.value ? dragValue.value : props.modelValue
)
const percent = computed(() =>
  props.max > 0
    ? Math.max(0, Math.min(100, (shown.value / props.max) * 100))
    : 0
)

function valueAt(event) {
  const rect = track.value.getBoundingClientRect()
  const ratio = Math.max(
    0,
    Math.min(1, (event.clientX - rect.left) / rect.width)
  )
  return ratio * props.max
}

function onDown(event) {
  if (event.button !== 0) return
  dragging.value = true
  dragValue.value = valueAt(event)
  emit('update:modelValue', dragValue.value)
  track.value.setPointerCapture(event.pointerId)
  const move = (e) => {
    dragValue.value = valueAt(e)
    emit('update:modelValue', dragValue.value)
  }
  const up = () => {
    dragging.value = false
    emit('commit', dragValue.value)
    track.value.removeEventListener('pointermove', move)
    track.value.removeEventListener('pointerup', up)
    track.value.removeEventListener('pointercancel', up)
  }
  track.value.addEventListener('pointermove', move)
  track.value.addEventListener('pointerup', up)
  track.value.addEventListener('pointercancel', up)
}

function onKey(event) {
  const delta = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[
    event.key
  ]
  if (!delta) return
  event.preventDefault()
  event.stopPropagation()
  const next = Math.max(
    0,
    Math.min(props.max, props.modelValue + delta * props.step)
  )
  emit('update:modelValue', next)
  emit('commit', next)
}
</script>
