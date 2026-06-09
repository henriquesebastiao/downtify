<template>
  <div v-if="totalItems > 0" class="mt-8 space-y-4">
    <div
      class="flex flex-wrap items-center justify-center gap-3 text-xs text-base-content/50"
    >
      <span>{{ rangeLabel }}</span>
      <label class="flex items-center gap-2">
        <span>{{ t('library.pageSize') }}</span>
        <select
          class="select select-bordered select-xs rounded-full bg-base-100/85 min-h-8 h-8"
          :value="pageSize"
          @change="onPageSizeChange"
        >
          <option v-for="n in pageSizeOptions" :key="n" :value="n">
            {{ n }}
          </option>
        </select>
      </label>
    </div>

    <nav
      v-if="totalPages > 1"
      class="flex items-center justify-center gap-1 flex-wrap"
    >
      <button
        class="icon-btn"
        :disabled="currentPage <= 1"
        @click="emit('update:currentPage', 1)"
        :title="t('library.firstPage')"
      >
        <Icon
          icon="clarity:angle-double-line"
          class="h-4 w-4 rotate-[-90deg]"
        />
      </button>
      <button
        class="icon-btn"
        :disabled="currentPage <= 1"
        @click="emit('update:currentPage', currentPage - 1)"
        :title="t('common.previousPage')"
      >
        <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-[-90deg]" />
      </button>

      <template v-for="(page, index) in pageButtons" :key="`${page}-${index}`">
        <span
          v-if="page === '…'"
          class="px-2 text-sm text-base-content/40 select-none"
          >…</span
        >
        <button
          v-else
          class="h-10 min-w-[2.5rem] rounded-full px-3 text-sm font-medium transition-colors"
          :class="
            page === currentPage
              ? 'bg-primary text-primary-content shadow-glow-sm'
              : 'text-base-content/70 hover:text-base-content hover:bg-white/10'
          "
          @click="emit('update:currentPage', page)"
        >
          {{ page }}
        </button>
      </template>

      <button
        class="icon-btn"
        :disabled="currentPage >= totalPages"
        @click="emit('update:currentPage', currentPage + 1)"
        :title="t('common.nextPage')"
      >
        <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-90" />
      </button>
      <button
        class="icon-btn"
        :disabled="currentPage >= totalPages"
        @click="emit('update:currentPage', totalPages)"
        :title="t('library.lastPage')"
      >
        <Icon icon="clarity:angle-double-line" class="h-4 w-4 rotate-90" />
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { useI18n } from '../i18n'
import { paginationRange } from '../utils/pagination'

const props = defineProps({
  currentPage: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  totalItems: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  pageSizeOptions: {
    type: Array,
    default: () => [10, 25, 50, 100],
  },
})

const emit = defineEmits(['update:currentPage', 'update:pageSize'])

const { t } = useI18n()

const pageButtons = computed(() =>
  paginationRange(props.currentPage, props.totalPages)
)

const rangeLabel = computed(() => {
  if (props.totalItems === 0) return ''
  const from = (props.currentPage - 1) * props.pageSize + 1
  const to = Math.min(props.currentPage * props.pageSize, props.totalItems)
  return t('library.showingRange', {
    from,
    to,
    total: props.totalItems,
  })
})

function onPageSizeChange(event) {
  const value = parseInt(event.target.value, 10)
  if (!Number.isNaN(value)) emit('update:pageSize', value)
}
</script>
