<template>
  <div class="karaoke-smoke" :class="{ 'is-paused': !playing }">
    <span
      v-for="(puff, i) in PUFFS"
      :key="i"
      class="karaoke-smoke-puff"
      :style="puffStyle(puff, i)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  palette: { type: Object, default: null },
  playing: { type: Boolean, default: false },
})

// Fixed rather than random, so the stage looks the same on every visit.
// `x`/`y` is where a puff is headed, as viewport percentages from the
// top-right corner: fanned out around the way to the middle of the screen.
const PUFFS = [
  { x: -66, y: 20, size: 40, seconds: 9, delay: 0, turn: 40 },
  { x: -60, y: 32, size: 44, seconds: 11, delay: -3, turn: -36 },
  { x: -54, y: 42, size: 38, seconds: 8, delay: -5, turn: 50 },
  { x: -48, y: 46, size: 46, seconds: 10, delay: -1.5, turn: -44 },
  { x: -40, y: 48, size: 36, seconds: 9, delay: -7, turn: 30 },
  { x: -30, y: 52, size: 42, seconds: 12, delay: -8, turn: -30 },
  { x: -20, y: 58, size: 38, seconds: 10, delay: -6, turn: 24 },
  { x: -12, y: 64, size: 40, seconds: 11, delay: -10, turn: -20 },
]

const FALLBACK = ['#8f9bc4', '#c4b5e0', '#86aec2']
// The one texture, turned differently per puff so they don't look alike.
const SPIN_STEP = 47

const colors = computed(() => {
  const { primary, soft, secondary } = props.palette || {}
  return primary ? [primary, soft, secondary] : FALLBACK
})

function puffStyle(puff, i) {
  return {
    '--puff': colors.value[i % colors.value.length],
    width: `${puff.size}vmax`,
    height: `${puff.size}vmax`,
    margin: `${-puff.size / 2}vmax 0 0 ${-puff.size / 2}vmax`,
    animationDuration: `${puff.seconds}s`,
    animationDelay: `${puff.delay}s`,
    '--to-x': `${puff.x}vw`,
    '--to-y': `${puff.y}vh`,
    '--spin': `${i * SPIN_STEP}deg`,
    '--turn': `${puff.turn}deg`,
  }
}
</script>

<style scoped>
/* Lives in the backdrop, under the words. Past the diagonal through the
   middle of the screen there's no smoke at all, and the band around the
   line being sung is cleared too. */
.karaoke-smoke {
  position: absolute;
  inset: 0;
  overflow: hidden;
  mask-image:
    linear-gradient(to bottom left, #000 28%, transparent 50%),
    radial-gradient(ellipse 58% 30% at 50% 51%, transparent 55%, #000 100%);
  mask-composite: intersect;
}
/* Cloud noise cut into a soft round puff: without the noise it's only a
   glow, lost against the blurred artwork. Only transform and opacity move,
   so the noise is drawn once and not on every frame. */
.karaoke-smoke-puff {
  position: absolute;
  top: 0;
  left: 100%;
  opacity: 0;
  background-color: color-mix(in srgb, var(--puff) 60%, white);
  mask-image:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400'%3E%3Cfilter id='s' x='0' y='0' width='100%25' height='100%25' color-interpolation-filters='sRGB'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.012' numOctaves='4' seed='7'/%3E%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 2.4 0 0 0 -0.8'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23s)'/%3E%3C/svg%3E"),
    radial-gradient(closest-side, #000 25%, transparent);
  mask-size: 100% 100%;
  mask-composite: intersect;
  will-change: transform, opacity;
  animation-name: karaoke-smoke-roll;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
.is-paused .karaoke-smoke-puff {
  animation-play-state: paused;
}
@keyframes karaoke-smoke-roll {
  0% {
    opacity: 0;
    transform: translate3d(8vw, -8vh, 0) scale(0.6) rotate(var(--spin));
  }
  12%,
  60% {
    opacity: 0.8;
  }
  100% {
    opacity: 0;
    transform: translate3d(var(--to-x), var(--to-y), 0) scale(1.25)
      rotate(calc(var(--spin) + var(--turn)));
  }
}
@media (prefers-reduced-motion: reduce) {
  .karaoke-smoke {
    display: none;
  }
}
</style>
