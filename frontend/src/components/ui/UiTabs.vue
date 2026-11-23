<template>
  <!-- The line is the wrapper's border, and the tabs scroll sideways in
       their own box: the active tab's bar hangs 1px below its tab, over that
       line, so the box needs 1px of room there (pb-px, pulled back by -mb-px).
       Without it the bar was 1px of vertical overflow, which
       overflow-x-auto turns into a scrollbar-less vertical scroll: the wheel
       moved the tabs by a pixel and cut the counter's top border. -->
  <div class="border-b border-line">
    <div
      ref="list"
      role="tablist"
      class="relative -mb-px flex gap-6 overflow-x-auto overflow-y-hidden pb-px [scrollbar-width:none] sm:gap-7"
    >
      <component
        :is="item.to ? RouterLink : 'button'"
        v-for="item in items"
        :key="item.id"
        :to="item.to || undefined"
        :type="item.to ? undefined : 'button'"
        role="tab"
        :aria-selected="item.id === modelValue"
        class="group relative flex shrink-0 items-center gap-2 pb-3 whitespace-nowrap transition-colors duration-(--dur-fast)"
        @click="$emit('update:modelValue', item.id)"
      >
        <span
          class="eyebrow transition-colors duration-(--dur-fast)"
          :class="
            item.id === modelValue
              ? '!text-fg'
              : '!text-muted group-hover:!text-fg-3'
          "
          >{{ item.label }}</span
        >
        <UiBadge
          v-if="item.count !== undefined && item.count !== null"
          :tone="item.id === modelValue ? 'accent' : 'neutral'"
        >
          {{ item.count }}
        </UiBadge>
      </component>
      <!-- One bar for every tab, sliding to the active one: it shows where
           the page went. A 1px bar stretched to the tab's width, so moving
           it is a transform. -->
      <span
        v-if="bar.width"
        class="pointer-events-none absolute bottom-0 left-0 h-0.5 w-px origin-left rounded-full bg-accent"
        :class="
          animate
            ? 'transition-transform duration-(--dur-slow) ease-in-out-soft'
            : ''
        "
        :style="{
          transform: `translateX(${bar.left}px) scaleX(${bar.width})`,
        }"
        aria-hidden="true"
      />
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useResizeObserver } from '@vueuse/core'
import UiBadge from './UiBadge.vue'

const props = defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const list = ref(null)
const bar = ref({ left: 0, width: 0 })
// The bar is put in place without sliding when the tabs first show up.
const animate = ref(false)

function measure() {
  const tab = list.value?.querySelector('[aria-selected="true"]')
  bar.value = tab
    ? { left: tab.offsetLeft, width: tab.offsetWidth }
    : { left: 0, width: 0 }
}

watch(
  () => [props.modelValue, props.items],
  () => nextTick(measure),
  { deep: true }
)
useResizeObserver(list, measure)
onMounted(() => {
  measure()
  // The labels change width once the web font is in.
  document.fonts?.ready.then(measure)
  requestAnimationFrame(() => (animate.value = true))
})
</script>
