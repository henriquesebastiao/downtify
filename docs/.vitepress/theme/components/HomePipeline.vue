<template>
  <ol class="not-doc my-6 flex flex-col gap-2 md:flex-row md:items-stretch">
    <template v-for="(step, i) in steps" :key="step.title">
      <li
        class="flex flex-1 flex-col gap-3 rounded-panel border border-line-2 bg-surface p-5"
      >
        <span class="flex items-center justify-between">
          <span
            class="flex size-10 items-center justify-center rounded-[12px] bg-accent text-on-accent"
          >
            <Icon :name="step.icon" :size="20" :stroke-width="2" />
          </span>
          <span
            class="text-display text-[13px] font-semibold tracking-[0.08em] text-faint"
            >{{ String(i + 1).padStart(2, '0') }}</span
          >
        </span>
        <span class="text-display text-[16px] font-semibold text-fg">{{
          step.title
        }}</span>
        <span class="text-[13.5px] leading-relaxed text-muted">{{
          step.text
        }}</span>
      </li>
      <li
        v-if="i < steps.length - 1"
        aria-hidden="true"
        class="flex items-center justify-center text-accent max-md:rotate-90"
      >
        <Icon name="chevron-right" :size="18" :stroke-width="2.2" />
      </li>
    </template>
  </ol>
</template>

<script setup>
import Icon from './Icon.vue'

// steps: [{ icon, title, text }]
defineProps({ steps: { type: Array, required: true } })
</script>
