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
    class="group relative cursor-pointer touch-none outline-none"
    :style="{ height: `${HEIGHT}px` }"
    @pointerdown="onDown"
    @keydown="onKey"
  >
    <canvas
      ref="canvas"
      class="absolute inset-0 size-full"
      aria-hidden="true"
    />
    <span
      ref="thumb"
      class="absolute size-[22px] -translate-x-1/2 -translate-y-1/2 rounded-full shadow-[0_2px_8px_rgb(0_0_0/0.35)] transition-transform duration-150 group-focus-visible:ring-2 group-focus-visible:ring-white group-focus-visible:ring-offset-2 group-focus-visible:ring-offset-black/40"
      :class="dragging ? 'scale-110' : 'group-hover:scale-110'"
      :style="{
        top: `${BAR_Y}px`,
        backgroundColor: palette?.soft || '#ffffff',
      }"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useSlider } from './useSlider'
import { hexToRgb, mixRgb } from '/src/lib/palette'
import { advancePlayhead, createPlayhead, reportTime } from '/src/lib/playhead'
import { WAVE_LAYERS, waveHeight } from '/src/lib/wave'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 5 },
  label: { type: String, default: '' },
  valueText: { type: String, default: undefined },
  playing: { type: Boolean, default: false },
  // { primary, secondary, soft } from useCoverPalette, or null.
  palette: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'commit'])

const { track, dragging, onDown, onKey } = useSlider(props, emit)

// Waves rise above a thick bar that sits near the bottom of the box.
const HEIGHT = 48
const BAR_Y = 35
const BAR = 10
const WAVE_MAX = 26

const FALLBACK = { primary: '#ffffff', secondary: '#c9ced6', soft: '#ffffff' }
const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

const canvas = ref(null)
const thumb = ref(null)
let ctx = null
let frame = 0
let lastTime = 0
let clock = 0
let level = 0
let colors = null
// Playback time as drawn: glides between the browser's time reports.
const playhead = createPlayhead(props.modelValue, 0)
let shownPercent = 0

function targetColors() {
  const source = props.palette || FALLBACK
  return Object.fromEntries(
    Object.keys(FALLBACK).map((key) => [key, hexToRgb(source[key])])
  )
}

const css = (rgb, alpha = 1) =>
  `rgb(${rgb.map(Math.round).join(' ')} / ${alpha})`

function pill(x, width) {
  const r = BAR / 2
  ctx.beginPath()
  ctx.roundRect(x, BAR_Y - r, Math.max(width, BAR), BAR, r)
  ctx.fill()
}

function draw() {
  const el = canvas.value
  if (!el) return
  const dpr = window.devicePixelRatio || 1
  const width = el.clientWidth
  if (el.width !== Math.round(width * dpr)) {
    el.width = Math.round(width * dpr)
    el.height = Math.round(HEIGHT * dpr)
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, HEIGHT)

  const end = (width * shownPercent) / 100

  ctx.fillStyle = 'rgb(255 255 255 / 0.2)'
  pill(0, width)

  if (level > 0.005 && end > 2) {
    for (const layer of WAVE_LAYERS) {
      ctx.fillStyle = css(colors[layer.color], layer.alpha)
      ctx.beginPath()
      ctx.moveTo(0, BAR_Y)
      for (let x = 0; x <= end; x += 2) {
        const h = waveHeight(layer, x, end, clock) * WAVE_MAX * level
        ctx.lineTo(x, BAR_Y - h)
      }
      ctx.lineTo(end, BAR_Y)
      ctx.closePath()
      ctx.fill()
    }
  }

  ctx.fillStyle = css(colors.primary)
  pill(0, end)

  // Moved here rather than through a binding: it changes every frame.
  if (thumb.value) thumb.value.style.left = `${shownPercent}%`
}

function step(time) {
  frame = 0
  const dt = lastTime ? Math.min(0.05, (time - lastTime) / 1000) : 0
  lastTime = time

  const playing = props.playing && !dragging.value
  const shown = advancePlayhead(playhead, {
    now: time,
    dt,
    playing,
    max: props.max,
  })
  shownPercent = props.max > 0 ? (shown / props.max) * 100 : 0

  const animate = !reducedMotion.value
  const wantLevel = props.playing || dragging.value ? 1 : 0
  const targetLevel = animate ? wantLevel : wantLevel * 0.6
  level = animate
    ? level + (targetLevel - level) * Math.min(1, dt * 4)
    : targetLevel
  if (animate && level > 0.005) clock += dt

  const target = targetColors()
  let moving = false
  for (const key of Object.keys(target)) {
    const next = animate
      ? mixRgb(colors[key], target[key], Math.min(1, dt * 3))
      : target[key]
    moving ||= next.some((v, i) => Math.abs(v - target[key][i]) > 0.5)
    colors[key] = next
  }

  draw()

  const settled = Math.abs(level - targetLevel) < 0.005 && !moving
  // The playhead glides while playing even when motion is reduced: it's
  // progress, not decoration.
  if (playing || (animate && (level > 0.005 || !settled))) schedule()
  else lastTime = 0
}

function schedule() {
  if (!frame && !document.hidden) frame = requestAnimationFrame(step)
}

let resizeObserver = null
function onVisibility() {
  if (document.hidden) {
    cancelAnimationFrame(frame)
    frame = 0
    lastTime = 0
  } else {
    schedule()
  }
}

onMounted(() => {
  ctx = canvas.value.getContext('2d')
  colors = targetColors()
  level = props.playing ? 1 : 0
  reportTime(playhead, props.modelValue, performance.now())
  playhead.shown = props.modelValue
  resizeObserver = new ResizeObserver(schedule)
  resizeObserver.observe(canvas.value)
  document.addEventListener('visibilitychange', onVisibility)
  schedule()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  resizeObserver?.disconnect()
  document.removeEventListener('visibilitychange', onVisibility)
})

watch(
  () => props.modelValue,
  (value) => {
    reportTime(playhead, value, performance.now())
    schedule()
  }
)

watch(
  () => [
    props.max,
    props.playing,
    props.palette,
    dragging.value,
    reducedMotion.value,
  ],
  schedule
)
</script>
