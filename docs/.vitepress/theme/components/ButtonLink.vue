<template>
  <a
    :href="href"
    :target="external ? '_blank' : undefined"
    :rel="external ? 'noopener' : undefined"
    class="inline-flex h-11 items-center justify-center gap-2 rounded-control px-5 text-sm font-semibold transition-colors"
    :class="
      primary
        ? 'bg-accent text-on-accent hover:bg-accent-hi'
        : 'border border-line-3 bg-surface text-fg hover:border-muted/60 hover:bg-surface-2'
    "
  >
    <Icon v-if="icon" :name="icon" :size="17" />
    <slot>{{ text }}</slot>
    <Icon v-if="external && !icon" name="arrow-up-right" :size="15" />
  </a>
</template>

<script setup>
import { computed } from 'vue'
import { withBase } from 'vitepress'
import Icon from './Icon.vue'

const props = defineProps({
  link: { type: String, required: true },
  text: { type: String, default: '' },
  icon: { type: String, default: '' },
  primary: { type: Boolean, default: false },
})

const external = computed(() => /^https?:/.test(props.link))
const href = computed(() =>
  external.value ? props.link : withBase(props.link)
)
</script>
