<template>
  <!-- Desktop: room for the full boundary/sibling window. -->
  <nav class="mt-8 hidden items-center justify-center gap-1 sm:flex">
    <button
      class="icon-btn"
      :disabled="modelValue === 1"
      @click="$emit('update:modelValue', modelValue - 1)"
      :title="t('common.previousPage')"
    >
      <Icon icon="fa6-solid:chevron-up" class="h-4 w-4 rotate-[-90deg]" />
    </button>

    <template v-for="(item, index) in desktopItems" :key="`${item}-${index}`">
      <span
        v-if="item === 'ellipsis'"
        class="flex h-10 min-w-[2.5rem] items-center justify-center text-sm text-base-content/40 select-none"
        aria-hidden="true"
      >
        …
      </span>
      <button
        v-else
        class="h-10 min-w-[2.5rem] rounded-full px-3 text-sm font-medium transition-colors"
        :class="
          item === modelValue
            ? 'bg-primary text-primary-content shadow-glow-sm'
            : 'text-base-content/70 hover:text-base-content hover:bg-white/10'
        "
        @click="$emit('update:modelValue', item)"
      >
        {{ item }}
      </button>
    </template>

    <button
      class="icon-btn"
      :disabled="modelValue === totalPages"
      @click="$emit('update:modelValue', modelValue + 1)"
      :title="t('common.nextPage')"
    >
      <Icon icon="fa6-solid:chevron-up" class="h-4 w-4 rotate-90" />
    </button>
  </nav>

  <!-- Mobile: a much tighter window (first, current ± nothing, last)
       with smaller buttons, in a non-wrapping row — a phone-width
       screen has no room for the desktop layout's 9+ buttons without
       spilling onto a second line (henriquesebastiao/downtify mobile
       report: page 36 of 41 wrapped into two rows). Scrolls
       horizontally instead of wrapping in the unlikely case an even
       narrower viewport still doesn't have room. -->
  <nav
    class="mt-8 flex flex-nowrap items-center justify-center gap-0.5 overflow-x-auto sm:hidden"
  >
    <button
      class="icon-btn h-9 w-9 shrink-0"
      :disabled="modelValue === 1"
      @click="$emit('update:modelValue', modelValue - 1)"
      :title="t('common.previousPage')"
    >
      <Icon icon="fa6-solid:chevron-up" class="h-4 w-4 rotate-[-90deg]" />
    </button>

    <template v-for="(item, index) in mobileItems" :key="`${item}-${index}`">
      <span
        v-if="item === 'ellipsis'"
        class="flex h-9 min-w-[2rem] shrink-0 items-center justify-center text-xs text-base-content/40 select-none"
        aria-hidden="true"
      >
        …
      </span>
      <button
        v-else
        class="h-9 min-w-[2rem] shrink-0 rounded-full px-2 text-xs font-medium transition-colors"
        :class="
          item === modelValue
            ? 'bg-primary text-primary-content shadow-glow-sm'
            : 'text-base-content/70 hover:text-base-content hover:bg-white/10'
        "
        @click="$emit('update:modelValue', item)"
      >
        {{ item }}
      </button>
    </template>

    <button
      class="icon-btn h-9 w-9 shrink-0"
      :disabled="modelValue === totalPages"
      @click="$emit('update:modelValue', modelValue + 1)"
      :title="t('common.nextPage')"
    >
      <Icon icon="fa6-solid:chevron-up" class="h-4 w-4 rotate-90" />
    </button>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from '../i18n'
import { paginationItems, mobilePaginationItems } from '../model/pagination'

const props = defineProps({
  modelValue: { type: Number, required: true },
  totalPages: { type: Number, required: true },
})
defineEmits(['update:modelValue'])

const { t } = useI18n()

// Condensed page list (e.g. 1 2 3 … 36 37 38) instead of one button per
// page — showing every page number stopped being practical once a
// library/search/queue grew past a handful of pages (see the
// pagination.js docstring for the exact algorithm). Two separate,
// differently-sized variants are rendered — one per breakpoint, see
// the template — rather than one that reflows, so mobile always gets
// a layout that's actually been checked to fit a single row.
const desktopItems = computed(() =>
  paginationItems(props.modelValue, props.totalPages)
)
const mobileItems = computed(() =>
  mobilePaginationItems(props.modelValue, props.totalPages)
)
</script>
