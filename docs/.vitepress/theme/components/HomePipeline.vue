<template>
  <ol
    class="not-doc my-6 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch"
  >
    <template v-for="(step, i) in steps" :key="step.title">
      <li
        class="flex items-center gap-4 rounded-panel border border-line-2 bg-surface px-5 py-4"
      >
        <span
          class="text-display flex size-10 shrink-0 items-center justify-center rounded-full bg-accent/12 text-sm font-bold text-accent"
          >{{ i + 1 }}</span
        >
        <span class="min-w-0">
          <span class="block font-semibold text-fg">{{ step.title }}</span>
          <span class="block text-[13px] text-muted">{{ step.text }}</span>
        </span>
      </li>
      <li
        v-if="i < steps.length - 1"
        aria-hidden="true"
        class="flex items-center justify-center text-faint max-md:rotate-90"
      >
        <Icon name="arrow-right" :size="18" />
      </li>
    </template>
  </ol>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({ steps: { type: Array, required: true } })
</script>
