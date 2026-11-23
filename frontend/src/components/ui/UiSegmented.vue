<template>
  <div
    ref="root"
    class="relative inline-flex h-10 shrink-0 gap-0.5 rounded-control border border-line-2 bg-surface p-[3px]"
    role="radiogroup"
  >
    <!-- The pill behind the chosen option, one for all of them: it glides
         to the new choice. Clipped to the option's box rather than moved
         and stretched, so its corners keep their shape whatever the
         options' widths. -->
    <span
      v-if="clip"
      class="pointer-events-none absolute inset-0 bg-raised"
      :class="
        animate
          ? 'transition-[clip-path] duration-(--dur-base) ease-in-out-soft'
          : ''
      "
      :style="{ clipPath: clip }"
      aria-hidden="true"
    />
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      :aria-checked="option.value === modelValue"
      :title="option.label"
      :aria-label="option.label"
      class="relative flex min-w-9 items-center justify-center gap-1.5 rounded-[7px] px-2 text-[13px] font-medium transition-colors duration-(--dur-fast)"
      :class="
        option.value === modelValue ? 'text-fg' : 'text-faint hover:text-fg-3'
      "
      @click="$emit('update:modelValue', option.value)"
    >
      <AppIcon v-if="option.icon" :name="option.icon" :size="16" />
      <span v-if="showLabels">{{ option.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useResizeObserver } from '@vueuse/core'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  options: { type: Array, required: true },
  modelValue: { type: [String, Number], default: '' },
  showLabels: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const root = ref(null)
const clip = ref('')
const animate = ref(false)

function measure() {
  const box = root.value
  const option = box?.querySelector('[aria-checked="true"]')
  if (!option) {
    clip.value = ''
    return
  }
  const right = box.clientWidth - option.offsetLeft - option.offsetWidth
  const bottom = box.clientHeight - option.offsetTop - option.offsetHeight
  clip.value = `inset(${option.offsetTop}px ${right}px ${bottom}px ${option.offsetLeft}px round 7px)`
}

watch(
  () => [props.modelValue, props.options, props.showLabels],
  () => nextTick(measure),
  { deep: true }
)
useResizeObserver(root, measure)
onMounted(() => {
  measure()
  document.fonts?.ready.then(measure)
  requestAnimationFrame(() => (animate.value = true))
})
</script>
