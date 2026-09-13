<template>
  <div
    ref="viewportEl"
    class="min-w-0 overflow-hidden"
    :class="[$attrs.class, { 'text-left': overflowing }]"
  >
    <span
      ref="textEl"
      class="inline-block whitespace-nowrap"
      :class="{ 'marquee-scrolling': overflowing }"
      :style="
        overflowing
          ? {
              '--marquee-distance': `-${distance}px`,
              animationDuration: `${duration}s`,
            }
          : null
      "
    >
      {{ text }}
    </span>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

// Renders `text` truncated (no wrap, no overflow) as long as it fits;
// once it's actually wider than its own box, it scrolls back and forth
// instead — the layout itself never grows or gains a scrollbar to
// accommodate a long track/artist name (see the Player widget, which
// used to do exactly that: widen on desktop, gain horizontal scroll on
// mobile).
defineOptions({ inheritAttrs: false })

const props = defineProps({
  text: { type: String, default: '' },
})

const viewportEl = ref(null)
const textEl = ref(null)
const overflowing = ref(false)
const distance = ref(0)
const duration = ref(8)

function measure() {
  const viewport = viewportEl.value
  const textNode = textEl.value
  if (!viewport || !textNode) return
  // Transforms don't affect scrollWidth, so this is accurate even
  // mid-animation — no need to reset anything before measuring.
  const overflow = textNode.scrollWidth - viewport.clientWidth
  if (overflow > 2) {
    distance.value = overflow
    // Slower for longer names rather than a fixed speed, so a name
    // twice as long doesn't zip by twice as fast.
    duration.value = Math.max(4, Math.min(20, 4 + overflow / 30))
    overflowing.value = true
  } else {
    overflowing.value = false
  }
}

let resizeObserver
onMounted(() => {
  measure()
  resizeObserver = new ResizeObserver(measure)
  if (viewportEl.value) resizeObserver.observe(viewportEl.value)
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})
// The DOM only reflects a new `text` after Vue's next render tick.
watch(
  () => props.text,
  () => nextTick(measure)
)
</script>

<style scoped>
.marquee-scrolling {
  animation-name: marquee-bounce;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}

/* Pauses at each end so the start/end of the name is actually
   readable, rather than continuously sliding. */
@keyframes marquee-bounce {
  0%,
  15% {
    transform: translateX(0);
  }
  45%,
  55% {
    transform: translateX(var(--marquee-distance));
  }
  85%,
  100% {
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .marquee-scrolling {
    animation: none;
  }
}
</style>
