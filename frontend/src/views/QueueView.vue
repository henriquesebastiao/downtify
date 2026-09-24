<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('queue.title')" :subtitle="subtitle">
      <UiButton
        v-if="counts.failed"
        variant="ghost"
        icon="retry"
        @click="dm.retryAllFailed()"
      >
        {{ t('queue.retryFailed', { count: counts.failed }) }}
      </UiButton>
      <UiButton
        v-if="counts.done"
        variant="ghost"
        icon="check"
        @click="dm.clearCompleted()"
      >
        {{ t('queue.clearDone', { count: counts.done }) }}
      </UiButton>
      <UiButton
        v-if="queue.length"
        variant="danger"
        icon="trash"
        @click="clearAll"
      >
        <span class="max-sm:sr-only">{{ t('queue.clearAll') }}</span>
      </UiButton>
    </PageHeader>

    <UiTabs :items="tabs" :model-value="tab" />

    <div class="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div class="flex min-w-0 flex-col gap-3">
        <UiEmpty
          v-if="!queue.length"
          icon="download"
          :title="t('queue.emptyTitle')"
          :body="t('queue.emptyBody')"
        >
          <UiButton variant="primary" icon="search" @click="ui.focusSearch()">
            {{ t('queue.emptyAction') }}
          </UiButton>
        </UiEmpty>

        <UiEmpty
          v-else-if="!items.length"
          :icon="tab === 'failed' ? 'check-circle' : 'clock'"
          :title="t(`queue.emptyTab.${tab}`)"
          :body="
            tab === 'active' && counts.queued
              ? t('queue.waitingHint', { count: counts.queued })
              : ''
          "
        />

        <div
          v-else
          ref="listRoot"
          class="relative"
          :style="{ height: `${totalSize}px` }"
        >
          <div
            v-for="row in rows"
            :key="row.item.key"
            :ref="measureRow"
            :data-index="row.index"
            class="absolute inset-x-0 top-0 pb-2"
            :style="{ transform: `translateY(${row.start}px)` }"
          >
            <QueueItem
              :item="row.item"
              :compact="
                row.item.state === 'queued' || row.item.state === 'done'
              "
            />
          </div>
        </div>
      </div>

      <aside class="flex flex-col gap-4 xl:sticky xl:top-[96px]">
        <UiPanel
          v-if="activeBatches.length"
          :title="t('queue.playlistDownloads')"
        >
          <ul class="flex flex-col gap-4">
            <li v-for="batch in activeBatches" :key="batch.spotify_playlist_id">
              <RouterLink
                :to="{ name: 'Playlist', query: { name: batch.playlist_name } }"
                class="flex items-center justify-between gap-3 text-sm"
              >
                <span class="truncate font-semibold hover:underline">{{
                  batch.playlist_name
                }}</span>
                <span class="tabular shrink-0 text-xs text-muted">
                  {{ batch.downloaded_count }} / {{ batch.expected_count }}
                </span>
              </RouterLink>
              <UiProgress
                class="mt-2"
                :value="
                  batch.expected_count
                    ? (batch.downloaded_count / batch.expected_count) * 100
                    : 0
                "
              />
            </li>
          </ul>
        </UiPanel>

        <UiPanel v-if="queue.length" :title="t('queue.sources')">
          <ul class="flex flex-col gap-2.5">
            <li
              v-for="source in sourceCounts"
              :key="source.id"
              class="flex items-center justify-between gap-3"
            >
              <SourceBadge :source="source.id" />
              <span class="tabular text-sm text-muted">{{ source.count }}</span>
            </li>
            <li v-if="!sourceCounts.length" class="text-[13px] text-muted">
              {{ t('queue.noSourcesYet') }}
            </li>
          </ul>
        </UiPanel>

        <UiPanel
          :title="t('queue.importTitle')"
          :description="t('queue.importHint')"
        >
          <CsvImport />
        </UiPanel>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiProgress from '/src/components/ui/UiProgress.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import SourceBadge from '/src/components/ui/SourceBadge.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import QueueItem from '/src/components/queue/QueueItem.vue'
import CsvImport from '/src/components/queue/CsvImport.vue'
import {
  useDownloadManager,
  useProgressTracker,
  syncQueueFromServer,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { queueRowEstimate } from '/src/lib/queueList'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const ui = useUi()
const listRoot = ref(null)
const scrollMargin = ref(0)

syncQueueFromServer().catch(() => {})

const queue = computed(() => {
  tracker.queueVersion.value
  return tracker.downloadQueue.value
})

const counts = computed(() => {
  const result = { active: 0, queued: 0, done: 0, failed: 0 }
  for (const item of queue.value) result[item.state] += 1
  return result
})

const TABS = ['active', 'queued', 'done', 'failed', 'all']
const tab = computed(() => {
  const requested = String(route.params.tab || '')
  if (TABS.includes(requested)) return requested
  return counts.value.active || counts.value.queued ? 'active' : 'all'
})

// Jump to "In progress" as soon as something starts downloading.
watch(
  () => counts.value.active,
  (now, before) => {
    if (now > (before ?? 0) && tab.value !== 'active') {
      router.replace({ name: 'Queue', params: { tab: 'active' } })
    }
  }
)

const tabs = computed(() =>
  [
    ['active', t('queue.tabActive'), counts.value.active],
    ['queued', t('queue.tabQueued'), counts.value.queued],
    ['done', t('queue.tabDone'), counts.value.done],
    ['failed', t('queue.tabFailed'), counts.value.failed],
    ['all', t('queue.tabAll'), queue.value.length],
  ].map(([id, label, count]) => ({
    id,
    label,
    count,
    to: { name: 'Queue', params: { tab: id } },
  }))
)

const ORDER = { active: 0, failed: 1, queued: 2, done: 3 }

const items = computed(() => {
  if (tab.value === 'all') {
    return [...queue.value].sort((a, b) => ORDER[a.state] - ORDER[b.state])
  }
  const list = queue.value.filter((item) => item.state === tab.value)
  // Newest finished first.
  return tab.value === 'done'
    ? list.sort((a, b) => b.updatedAt - a.updatedAt)
    : list
})

const virtualizer = useWindowVirtualizer(
  computed(() => ({
    count: items.value.length,
    estimateSize: (index) => queueRowEstimate(items.value[index]?.state),
    overscan: 8,
    scrollMargin: scrollMargin.value,
  }))
)

function measureOffset() {
  if (!listRoot.value) return
  scrollMargin.value =
    listRoot.value.getBoundingClientRect().top + window.scrollY
}

function measureRow(el) {
  if (el) virtualizer.value.measureElement(el)
}

onMounted(measureOffset)
watch(
  () => [tab.value, items.value.length],
  () => requestAnimationFrame(measureOffset)
)

const totalSize = computed(() => virtualizer.value.getTotalSize())
const rows = computed(() =>
  virtualizer.value
    .getVirtualItems()
    .map((row) => ({
      item: items.value[row.index],
      index: row.index,
      start: row.start - scrollMargin.value,
    }))
    .filter((row) => row.item)
)

const subtitle = computed(() => {
  if (!queue.value.length) return ''
  return [
    t('queue.countActive', { count: counts.value.active }),
    t('queue.countQueued', { count: counts.value.queued }),
    counts.value.failed
      ? t('queue.countFailed', { count: counts.value.failed })
      : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

const sourceCounts = computed(() => {
  const map = new Map()
  for (const item of queue.value) {
    if (item.state !== 'done' || !item.provider) continue
    map.set(item.provider, (map.get(item.provider) || 0) + 1)
  }
  return [...map.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => b.count - a.count)
})

const activeBatches = computed(() =>
  library.batches.value.filter(
    (batch) => batch.active_in_queue || batch.status === 'in_progress'
  )
)

// Keep playlist progress fresh while something is downloading.
watch(
  () => counts.value.done,
  () => library.refreshSoon(1500)
)

async function clearAll() {
  const ok = await ui.confirm({
    title: t('confirm.clearQueueTitle'),
    body: t('confirm.clearQueueBody'),
    confirmLabel: t('queue.clearAll'),
    danger: true,
  })
  if (ok) await dm.clearAll()
}
</script>
