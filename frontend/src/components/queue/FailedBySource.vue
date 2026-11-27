<template>
  <section
    class="rounded-[14px] border border-line-2 bg-surface p-4"
    :aria-label="t('queue.bySourceTitle')"
  >
    <p class="text-sm font-semibold">{{ t('queue.bySourceTitle') }}</p>
    <p class="mt-0.5 text-[13px] text-muted">
      {{ t('queue.bySourceHint') }}
    </p>
    <ul class="mt-3 flex flex-col gap-3">
      <li v-for="source in rows" :key="source.provider">
        <div class="flex items-center justify-between gap-3">
          <SourceBadge
            v-if="source.provider !== 'none'"
            :source="source.provider"
          />
          <span v-else class="text-sm font-semibold">{{ source.label }}</span>
          <span class="tabular text-sm text-muted">{{
            t('queue.bySourceSongs', { count: source.count })
          }}</span>
        </div>
        <ul class="mt-1.5 flex flex-col gap-1 pl-1">
          <li
            v-for="reason in source.reasons"
            :key="reason.text"
            class="flex items-start justify-between gap-3 text-[13px]"
          >
            <span class="min-w-0 break-words text-fg-3">{{ reason.text }}</span>
            <span class="tabular shrink-0 text-muted">{{ reason.count }}</span>
          </li>
        </ul>
      </li>
    </ul>
  </section>
</template>

<script setup>
// The Failed tab's "By source" summary: for every failed song, what each
// audio source said, counted (lib/sourceAttempts.js).
import { computed } from 'vue'
import SourceBadge from '../ui/SourceBadge.vue'
import { failureBreakdown } from '/src/lib/sourceAttempts'
import { useI18n } from '/src/i18n'

const props = defineProps({
  items: { type: Array, required: true },
})

const { t } = useI18n()
const rows = computed(() => failureBreakdown(props.items, t))
</script>
