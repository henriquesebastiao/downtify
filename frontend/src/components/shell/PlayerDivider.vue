<template>
  <div
    class="flex h-10 items-center justify-center rounded-control"
    :class="editable && 'cursor-col-resize touch-none select-none hover:bg-surface-2 focus-visible:bg-surface-2'"
    :role="editable ? 'separator' : undefined"
    :tabindex="editable ? 0 : undefined"
    :aria-label="editable ? label : undefined"
    :aria-orientation="editable ? 'vertical' : undefined"
    :aria-controls="editable ? controls : undefined"
    :aria-valuemin="editable ? limits.min : undefined"
    :aria-valuemax="editable ? limits.max : undefined"
    :aria-valuenow="editable ? limits.current : undefined"
  >
    <span v-if="editable" class="h-6 w-0.5 rounded-full bg-accent" />
  </div>
</template>

<script setup>
defineProps({
  editable: Boolean,
  label: String,
  controls: String,
  limits: Object,
})
</script>
