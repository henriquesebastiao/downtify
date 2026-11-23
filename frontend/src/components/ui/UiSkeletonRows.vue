<template>
  <!-- Rows of a list still loading: an optional cover and one or two lines
       of text, of varied lengths so they read as text rather than bars.
       `label` is what a screen reader hears meanwhile. -->
  <div class="flex flex-col" :class="gap" aria-busy="true">
    <span v-if="label" class="sr-only" role="status">{{ label }}</span>
    <div
      v-for="n in count"
      :key="n"
      class="flex items-center gap-3"
      :class="rowClass"
    >
      <UiSkeleton
        v-if="cover"
        class="shrink-0"
        :class="[cover, round ? '!rounded-full' : '!rounded-[8px]']"
      />
      <div class="flex min-w-0 flex-1 flex-col gap-2">
        <UiSkeleton class="h-3.5" :style="{ width: `${width(n)}%` }" />
        <UiSkeleton
          v-if="lines > 1"
          class="h-3"
          :style="{ width: `${Math.round(width(n) * 0.6)}%` }"
        />
      </div>
      <UiSkeleton v-if="action" class="size-8 shrink-0 !rounded-full" />
    </div>
  </div>
</template>

<script setup>
import UiSkeleton from './UiSkeleton.vue'

defineProps({
  count: { type: Number, default: 4 },
  // Size classes of the cover (e.g. 'size-11'), '' for none.
  cover: { type: String, default: 'size-11' },
  round: { type: Boolean, default: false },
  lines: { type: Number, default: 2 },
  // A round button at the end of each row (download, play...).
  action: { type: Boolean, default: false },
  // Height and padding of a row, to match the real one.
  rowClass: { type: String, default: 'h-16 px-3' },
  gap: { type: String, default: 'gap-1' },
  label: { type: String, default: '' },
})

const WIDTHS = [56, 42, 64, 48, 36, 60, 52]
const width = (n) => WIDTHS[(n - 1) % WIDTHS.length]
</script>
