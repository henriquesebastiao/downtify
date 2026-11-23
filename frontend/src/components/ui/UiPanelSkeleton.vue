<template>
  <!-- Panels still loading (a settings group, a card of figures): a title,
       its hint and a few rows, in the panel's own frame. -->
  <div class="flex flex-col gap-8" aria-busy="true">
    <span v-if="label" class="sr-only" role="status">{{ label }}</span>
    <section
      v-for="n in count"
      :key="n"
      class="overflow-hidden rounded-panel border border-line-2 bg-surface"
    >
      <div class="flex flex-col gap-2 px-5 pt-5 pb-4">
        <UiSkeleton class="h-4 w-40" />
        <UiSkeleton class="h-3 w-72 max-w-full" />
      </div>
      <div
        v-for="row in rows"
        :key="row"
        class="flex items-center justify-between gap-4 border-t border-line-2 px-5 py-4"
      >
        <div class="flex flex-1 flex-col gap-2">
          <UiSkeleton class="h-3.5 w-1/3" />
          <UiSkeleton class="h-3 w-1/2" />
        </div>
        <UiSkeleton class="h-5 w-9 !rounded-full" />
      </div>
    </section>
  </div>
</template>

<script setup>
import UiSkeleton from './UiSkeleton.vue'

defineProps({
  count: { type: Number, default: 1 },
  rows: { type: Number, default: 3 },
  label: { type: String, default: '' },
})
</script>
