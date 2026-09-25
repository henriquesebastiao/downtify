<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to || undefined"
    :type="to ? undefined : 'button'"
    :title="label"
    :aria-label="label"
    :aria-pressed="toggle ? active : undefined"
    :disabled="to ? undefined : disabled"
    class="inline-flex shrink-0 items-center justify-center transition-colors duration-150 disabled:opacity-40"
    :class="[
      round ? 'rounded-full' : 'rounded-control',
      sizeClass,
      photo
        ? 'bg-white/95 text-neutral-900 hover:bg-white'
        : active
          ? 'text-accent hover:bg-accent/10'
          : 'text-muted hover:bg-surface-2 hover:text-fg',
    ]"
  >
    <AppIcon :name="icon" :size="iconSize" />
    <slot />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  size: { type: String, default: 'md' },
  active: { type: Boolean, default: false },
  toggle: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  // Fixed light pill, independent of theme - see UiButton's 'photo'
  // variant for why (a control sitting on a banner image).
  photo: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  to: { type: [String, Object], default: null },
})

const sizeClass = computed(
  () =>
    ({ sm: 'size-8', md: 'size-10', lg: 'size-11' })[props.size] || 'size-10'
)
const iconSize = computed(() => ({ sm: 16, md: 18, lg: 20 })[props.size] || 18)
</script>
