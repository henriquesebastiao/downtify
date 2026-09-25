<template>
  <!-- The line is the wrapper's border, and the tabs scroll sideways in
       their own box: the active tab's bar hangs 1px below its tab, over that
       line, so the box needs 1px of room there (pb-px, pulled back by -mb-px).
       Without it the bar was 1px of vertical overflow, which
       overflow-x-auto turns into a scrollbar-less vertical scroll: the wheel
       moved the tabs by a pixel and cut the counter's top border. -->
  <div class="border-b border-line">
    <div
      role="tablist"
      class="-mb-px flex gap-6 overflow-x-auto overflow-y-hidden pb-px [scrollbar-width:none] sm:gap-7"
    >
      <component
        :is="item.to ? RouterLink : 'button'"
        v-for="item in items"
        :key="item.id"
        :to="item.to || undefined"
        :type="item.to ? undefined : 'button'"
        role="tab"
        :aria-selected="item.id === modelValue"
        class="group relative flex shrink-0 items-center gap-2 pb-3 whitespace-nowrap transition-colors"
        @click="$emit('update:modelValue', item.id)"
      >
        <span
          class="eyebrow"
          :class="
            item.id === modelValue
              ? '!text-fg'
              : '!text-muted group-hover:!text-fg-3'
          "
          >{{ item.label }}</span
        >
        <UiBadge
          v-if="item.count !== undefined && item.count !== null"
          :tone="item.id === modelValue ? 'accent' : 'neutral'"
        >
          {{ item.count }}
        </UiBadge>
        <span
          v-if="item.id === modelValue"
          class="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-accent"
        />
      </component>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import UiBadge from './UiBadge.vue'

defineProps({
  items: { type: Array, required: true },
  modelValue: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>
