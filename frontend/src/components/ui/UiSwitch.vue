<template>
  <label
    class="flex cursor-pointer items-start gap-3.5"
    :class="disabled ? 'cursor-not-allowed opacity-50' : ''"
  >
    <span class="min-w-0 flex-1" v-if="label || description || $slots.default">
      <span class="block text-sm font-semibold text-fg">{{ label }}</span>
      <span v-if="description" class="mt-0.5 block text-[13px] text-muted">
        {{ description }}
      </span>
      <slot />
    </span>
    <input
      type="checkbox"
      role="switch"
      class="peer sr-only"
      :aria-label="ariaLabel || undefined"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
    <span
      class="relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors duration-200 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent"
      :class="modelValue ? 'bg-accent' : 'bg-raised'"
      aria-hidden="true"
    >
      <span
        class="absolute top-0.5 size-4 rounded-full bg-white shadow transition-[left] duration-200 ease-out-soft"
        :class="modelValue ? 'left-[18px]' : 'left-0.5'"
      />
    </span>
  </label>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, default: '' },
  description: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  // Names the control when there is no visible `label`.
  ariaLabel: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
