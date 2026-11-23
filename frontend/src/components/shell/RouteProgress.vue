<template>
  <!-- Only while a page takes a moment to arrive (lib/routeProgress.js): a
       hairline growing along the top edge, filled and faded on arrival. -->
  <div
    class="pointer-events-none fixed inset-x-0 top-0 z-[110] h-0.5"
    aria-hidden="true"
  >
    <div
      class="h-full origin-left bg-accent transition-[scale,opacity] ease-out-soft"
      :class="bar.visible ? 'duration-(--dur-base)' : 'duration-(--dur-slow)'"
      :style="{ scale: `${bar.value} 1`, opacity: bar.visible ? 1 : 0 }"
    />
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createRouteProgress } from '/src/lib/routeProgress'

const router = useRouter()
const bar = ref({ visible: false, value: 0 })
const progress = createRouteProgress({
  onChange: (state) => (bar.value = state),
})

const stops = [
  // Opening Now playing (?np=1) or a tab's query isn't a page change.
  router.beforeEach((to, from) => {
    if (to.path !== from.path) progress.start()
  }),
  router.afterEach(() => progress.done()),
]
router.onError(() => progress.done())

onBeforeUnmount(() => stops.forEach((stop) => stop()))
</script>
