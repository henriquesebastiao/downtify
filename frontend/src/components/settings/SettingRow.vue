<template>
  <div
    class="flex gap-4 px-5 py-4"
    :class="
      stacked
        ? 'flex-col'
        : 'flex-col sm:flex-row sm:items-center sm:justify-between'
    "
  >
    <div class="min-w-0 sm:max-w-[60%]" :class="stacked ? 'sm:max-w-none' : ''">
      <p class="text-sm font-semibold text-fg">{{ label }}</p>
      <p v-if="description" class="mt-0.5 text-[13px] text-pretty text-muted">
        {{ description }}
      </p>
    </div>
    <div
      class="flex shrink-0 flex-wrap items-center gap-2"
      :class="stacked ? '' : 'sm:justify-end'"
    >
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  description: { type: String, default: '' },
  stacked: { type: Boolean, default: false },
})
</script>
