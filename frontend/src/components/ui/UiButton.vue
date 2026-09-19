<template>
  <component
    :is="tag"
    v-bind="linkAttrs"
    :type="tag === 'button' ? type : undefined"
    :disabled="tag === 'button' ? disabled || loading : undefined"
    :aria-disabled="disabled || loading || undefined"
    class="inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-control border font-semibold transition-colors duration-150 disabled:opacity-50"
    :class="[sizeClass, variantClass]"
  >
    <span
      v-if="loading"
      class="size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
    />
    <AppIcon v-else-if="icon" :name="icon" :size="iconSize" stroke-width="2" />
    <slot />
    <AppIcon
      v-if="iconRight"
      :name="iconRight"
      :size="iconSize"
      stroke-width="2"
    />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  variant: { type: String, default: 'secondary' },
  size: { type: String, default: 'md' },
  icon: { type: String, default: '' },
  iconRight: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  to: { type: [String, Object], default: null },
  href: { type: String, default: '' },
  type: { type: String, default: 'button' },
})

const tag = computed(() => {
  if (props.to) return RouterLink
  if (props.href) return 'a'
  return 'button'
})

const linkAttrs = computed(() => {
  if (props.to) return { to: props.to }
  if (props.href) return { href: props.href, target: '_blank', rel: 'noopener' }
  return {}
})

const sizeClass = computed(
  () =>
    ({
      sm: 'h-8 px-3 text-[13px]',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-5 text-[15px]',
    })[props.size] || 'h-10 px-4 text-sm'
)

const iconSize = computed(() => (props.size === 'sm' ? 14 : 16))

const variantClass = computed(
  () =>
    ({
      primary:
        'border-accent bg-accent text-on-accent hover:border-accent-hi hover:bg-accent-hi',
      secondary: 'border-line-3 bg-surface-2 text-fg hover:bg-raised',
      ghost:
        'border-line-2 bg-transparent text-fg-3 hover:border-line-3 hover:bg-surface-2 hover:text-fg',
      danger: 'border-transparent bg-danger/12 text-danger hover:bg-danger/20',
      invert: 'border-invert bg-invert text-on-invert hover:opacity-90',
      plain:
        'border-transparent bg-transparent text-muted hover:bg-surface-2 hover:text-fg',
    })[props.variant]
)
</script>
