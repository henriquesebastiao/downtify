<template>
  <section class="flex flex-col gap-1">
    <header v-if="title" class="mb-3">
      <h3 class="text-display text-base font-semibold">{{ title }}</h3>
      <p v-if="description" class="mt-1 text-[13px] text-pretty text-muted">
        {{ description }}
      </p>
    </header>
    <div
      class="flex flex-col divide-y divide-line rounded-panel border border-line-2 bg-surface"
    >
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
})
</script>
