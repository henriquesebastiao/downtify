<template>
  <div class="flex min-w-0 flex-col gap-1.5">
    <div class="flex items-center justify-between gap-2 text-xs">
      <span class="tabular truncate text-muted">
        <template v-if="batch?.expected_count">
          {{
            t('playlists.progress', {
              have: batch.downloaded_count,
              total: batch.expected_count,
            })
          }}
        </template>
        <template v-else>{{
          t('common.tracks', { count: playlist.tracks.length })
        }}</template>
      </span>
      <UiBadge v-if="state === 'downloading'" tone="accent">
        <EqBars :size="9" />{{
          t('playlists.downloading', { count: batch.active_in_queue })
        }}
      </UiBadge>
      <UiBadge v-else-if="state === 'missing'" tone="warn">
        {{ t('playlists.missingShort', { count: batch.missing_count }) }}
      </UiBadge>
      <UiBadge v-else-if="state === 'complete'" tone="accent" icon="check">
        {{ t('playlists.complete') }}
      </UiBadge>
    </div>
    <UiProgress
      v-if="batch?.expected_count"
      :value="percent"
      :color="state === 'missing' ? 'bg-warn' : 'bg-accent'"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EqBars from '../ui/EqBars.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiProgress from '../ui/UiProgress.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({ playlist: { type: Object, required: true } })
const { t } = useI18n()

const batch = computed(() => props.playlist.batch)

const state = computed(() => {
  const b = batch.value
  if (!b) return ''
  if (b.active_in_queue) return 'downloading'
  if (b.missing_count) return 'missing'
  if (b.expected_count) return 'complete'
  return ''
})

const percent = computed(() => {
  const b = batch.value
  if (!b?.expected_count) return 0
  return (b.downloaded_count / b.expected_count) * 100
})
</script>
