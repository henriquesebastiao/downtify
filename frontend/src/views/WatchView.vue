<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <RouterLink
      :to="backRoute"
      class="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-muted hover:text-fg"
    >
      <AppIcon name="arrow-left" :size="16" />{{ t('monitor.title') }}
    </RouterLink>

    <div v-if="loading && !watch" class="flex flex-col gap-3">
      <UiSkeleton class="h-10 w-1/2" />
      <UiSkeleton class="h-24 w-full !rounded-panel" />
      <UiSkeleton class="h-64 w-full !rounded-panel" />
    </div>

    <UiEmpty
      v-else-if="!watch"
      icon="radar"
      :title="t('watchStats.notFound')"
      :body="t('watchStats.notFoundHint')"
    >
      <UiButton :to="backRoute" icon="radar">{{ t('monitor.title') }}</UiButton>
    </UiEmpty>

    <template v-else>
      <PageHeader :title="watch.name" :subtitle="subtitle">
        <UiButton
          v-if="libraryRoute"
          variant="secondary"
          :icon="watch.kind === 'artist' ? 'user' : 'playlist'"
          :to="libraryRoute"
        >
          {{ t('watchStats.openInLibrary') }}
        </UiButton>
        <UiButton variant="ghost" icon="arrow-up-right" :href="watch.url">
          {{ t('monitor.openSource') }}
        </UiButton>
        <UiButton
          variant="ghost"
          icon="retry"
          :loading="checking"
          @click="check"
        >
          {{ t('monitor.checkNow') }}
        </UiButton>
      </PageHeader>
      <div class="-mt-3 flex min-w-0 flex-wrap items-center gap-2">
        <WatchSourceBadge :source="watch.source" />
        <UiBadge>#{{ watch.id }}</UiBadge>
        <UiBadge v-if="!watch.enabled" tone="warn">{{
          t('monitor.activeOff')
        }}</UiBadge>
        <a
          :href="watch.url"
          target="_blank"
          rel="noopener"
          :title="watch.url"
          class="min-w-0 truncate font-mono text-[11.5px] text-muted hover:text-fg hover:underline"
          >{{ watch.url }}</a
        >
      </div>

      <div
        v-if="stats"
        class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6"
      >
        <div
          v-for="tile in tiles"
          :key="tile.key"
          class="min-w-0 rounded-panel border border-line-2 bg-surface px-4 py-3"
        >
          <p
            class="truncate text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
          >
            {{ tile.label }}
          </p>
          <p class="tabular mt-1 text-xl font-semibold" :class="tile.tone">
            {{ tile.value }}
          </p>
          <p v-if="tile.hint" class="mt-0.5 text-[12px] text-pretty text-muted">
            {{ tile.hint }}
          </p>
        </div>
      </div>
      <p v-else-if="statsError" class="text-[13px] text-danger" role="alert">
        {{ t('watchStats.statsFailed') }}
      </p>
      <ul
        v-if="notes.length"
        class="-mt-3 flex flex-col gap-1 text-[13px] text-muted"
      >
        <li v-for="note in notes" :key="note" class="flex items-start gap-2">
          <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />{{ note }}
        </li>
      </ul>

      <UiPanel
        v-if="stats"
        :title="t('watchStats.activityTitle')"
        :description="t('watchStats.activityHint')"
      >
        <template #actions>
          <UiSegmented
            v-model="days"
            :options="periodOptions"
            show-labels
            class="max-sm:hidden"
          />
        </template>
        <UiSegmented
          v-model="days"
          :options="periodOptions"
          show-labels
          class="mb-4 sm:hidden"
        />
        <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div class="min-w-0">
            <p class="text-display tabular text-4xl font-bold">
              {{ stats.period.added }}
            </p>
            <p class="text-sm text-muted">
              {{ t('watchStats.newSongsLabel', { count: stats.period.added }) }}
            </p>
            <dl class="mt-4 grid grid-cols-3 gap-3">
              <div v-for="rate in rates" :key="rate.key" class="min-w-0">
                <dt class="truncate text-[12px] text-muted">
                  {{ rate.label }}
                </dt>
                <dd class="tabular text-base font-semibold">
                  {{ rate.value }}
                </dd>
              </div>
            </dl>
            <p class="mt-4 flex items-center gap-2 text-sm font-medium">
              <AppIcon
                :name="trend.icon"
                :size="18"
                :class="[
                  trend.flip ? '-scale-y-100' : '',
                  stats.trend.direction === 'up' ? 'text-accent' : 'text-muted',
                ]"
              />{{ t(trend.label) }}
            </p>
            <ul class="mt-3 flex flex-col gap-1 text-[13px] text-muted">
              <li v-for="line in periodLines" :key="line">{{ line }}</li>
            </ul>
          </div>
          <div v-if="bars.length" class="min-w-0">
            <p
              class="mb-2 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
            >
              {{
                data?.bucket_days === 1
                  ? t('watchStats.barsPerDay')
                  : t('watchStats.barsPerWeek')
              }}
            </p>
            <svg
              class="h-32 w-full text-accent"
              :viewBox="`0 0 ${bars.length * 10} 100`"
              preserveAspectRatio="none"
              role="img"
              :aria-label="seriesLabel"
            >
              <rect
                v-for="bar in bars"
                :key="bar.x"
                :x="bar.x + 1"
                :y="100 - bar.height"
                width="8"
                :height="bar.height"
                rx="1.5"
                fill="currentColor"
                :opacity="bar.count ? 1 : 0.18"
              >
                <title>{{ bar.count }}</title>
              </rect>
            </svg>
          </div>
        </div>
      </UiPanel>

      <UiPanel
        v-if="providerRows.length"
        :title="t('watchStats.providersTitle')"
      >
        <ul class="flex flex-col gap-3">
          <li v-for="row in providerRows" :key="row.id" class="text-sm">
            <div class="flex items-center justify-between gap-3">
              <span class="truncate">{{ row.label }}</span>
              <span class="tabular text-muted">{{ row.count }}</span>
            </div>
            <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
              <div
                class="h-full rounded-full bg-accent"
                :style="{ width: `${Math.max(2, row.share * 100)}%` }"
              />
            </div>
          </li>
        </ul>
      </UiPanel>

      <UiPanel
        v-if="failures.length"
        :title="t('watchStats.failuresTitle', { count: failures.length })"
      >
        <ul class="flex flex-col divide-y divide-line-2">
          <li
            v-for="failure in failures"
            :key="failure.track_id"
            class="flex flex-col gap-0.5 py-2.5 first:pt-0 last:pb-0"
          >
            <span class="truncate text-sm font-semibold">
              {{ failure.name || failure.track_id }}
              <span v-if="failure.artists" class="font-normal text-muted">
                · {{ failure.artists }}</span
              >
            </span>
            <span class="text-[12px] text-muted">
              {{ t('watchStats.attempts', { count: failure.attempts }) }} ·
              {{
                t('watchStats.lastTried', {
                  when: timeAgo(failure.last_failed_at, locale),
                })
              }}
            </span>
            <span
              v-if="failure.error"
              class="truncate font-mono text-[11.5px] text-faint"
              :title="failure.error"
              >{{ failure.error }}</span
            >
          </li>
        </ul>
      </UiPanel>

      <section class="flex flex-col gap-3 pb-10">
        <div>
          <h2 class="text-display text-xl font-semibold">
            {{ t('watchStats.songsTitle') }}
          </h2>
          <p class="mt-1 text-[13px] text-pretty text-muted">
            {{ t('watchStats.songsHint') }}
          </p>
        </div>
        <UiChips v-model="filter" :items="filterChips" />
        <SelectionBar
          :count="selected.size"
          :total="shown.length"
          :zipping="zipping"
          @select-all="selected = new Set(shown.map((track) => track.file))"
          @clear="selected = new Set()"
          @play="actions.play(selectedTracks, 0, context)"
          @enqueue="actions.enqueue(selectedTracks)"
          @add-to-playlist="playlistActions.openCreate(selectedTracks)"
          @zip="zipSelected"
          @delete="deleteTracks(selectedTracks)"
        />
        <TrackList
          v-if="shown.length"
          v-model:selected="selected"
          :tracks="shown"
          :context="context"
        />
        <UiEmpty
          v-else
          icon="music"
          :title="t('watchStats.noSongs')"
          :body="t('watchStats.noSongsHint')"
        />
      </section>
    </template>
  </div>
</template>

<script setup>
// One Playlist Monitor watch: what it holds and adds over time, where the
// audio came from, the songs it keeps failing on, and every song it
// brought into the library (to play, or clean up) - see
// GET /api/monitor/stats and /api/monitor/playlists/{id}/tracks.
import { computed, onMounted, ref, watch as watchRef } from 'vue'
import { useRoute } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import SelectionBar from '/src/components/library/SelectionBar.vue'
import TrackList from '/src/components/library/TrackList.vue'
import WatchSourceBadge from '/src/components/monitor/WatchSourceBadge.vue'
import monitorAPI from '/src/model/monitor'
import { useLibrary } from '/src/model/library'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { useUi } from '/src/model/ui'
import { formatBytes, timeAgo } from '/src/lib/format'
import { normalizeTrack } from '/src/lib/library'
import {
  STAT_PERIODS,
  TRACK_FILTERS,
  formatRate,
  libraryRouteFor,
  matchesTrackFilter,
  providerBreakdown,
  providerLabelKey,
  sparkline,
  trackFilterCounts,
  trendDisplay,
} from '/src/lib/watchStats'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const route = useRoute()
const ui = useUi()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const library = useLibrary()

const watchId = computed(() => Number(route.params.id))
const watch = ref(null)
const tracks = ref([])
const failures = ref([])
const missing = ref(0)
const loading = ref(false)
const data = ref(null)
const statsError = ref(false)
const checking = ref(false)
const filter = ref('all')
const selected = ref(new Set())
const zipping = ref(false)
// Shared with the Monitor page.
const days = useLocalStorage('downtify-monitor-period', 30)
if (!STAT_PERIODS.includes(days.value)) days.value = 30

const stats = computed(
  () =>
    (data.value?.watches || []).find((row) => row.id === watchId.value) || null
)

const backRoute = computed(() => ({
  name: 'Monitor',
  params: { tab: watch.value?.kind === 'artist' ? 'artists' : 'playlists' },
}))
const libraryRoute = computed(() => libraryRouteFor(watch.value))
const context = computed(() => ({
  type: 'library',
  title: watch.value?.name || '',
}))

const subtitle = computed(() => {
  const created = new Date(watch.value?.created_at || '')
  if (Number.isNaN(created.getTime())) return ''
  return t('watchStats.since', {
    date: created.toLocaleDateString(locale.value),
  })
})

const tiles = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    {
      key: 'songs',
      label: t('watchStats.tileSongs'),
      value: s.storage.files,
      hint: formatBytes(s.storage.bytes),
    },
    {
      key: 'downloaded',
      label: t('watchStats.tileDownloaded'),
      value: s.status.downloaded,
      tone: 'text-accent',
    },
    {
      key: 'linked',
      label: t('watchStats.tileLinked'),
      value: s.status.linked,
    },
    {
      key: 'unique',
      label: t('watchStats.tileUnique'),
      value: formatBytes(s.storage.unique_bytes),
      hint: t('watchStats.tileUniqueHint', { count: s.storage.unique_files }),
    },
    {
      key: 'shared',
      label: t('watchStats.tileShared'),
      value: s.storage.shared_files,
      hint: t('watchStats.tileSharedHint', {
        size: formatBytes(s.storage.shared_bytes),
      }),
    },
    {
      key: 'failing',
      label: t('watchStats.tileFailing'),
      value: s.status.failing,
      tone: s.status.failing ? 'text-danger' : '',
    },
  ]
})

const notes = computed(() => {
  const s = stats.value
  const lines = []
  if (s?.status.unknown) {
    lines.push(t('watchStats.unknownNote', { count: s.status.unknown }))
  }
  if (missing.value) {
    lines.push(t('watchStats.missingNote', { count: missing.value }))
  }
  return lines
})

const periodOptions = computed(() =>
  STAT_PERIODS.map((value) => ({
    value,
    label: t('watchStats.days', { count: value }),
  }))
)

const rates = computed(() => {
  const rate = stats.value?.rate || {}
  return [
    { key: 'day', value: rate.per_day, label: 'watchStats.rateDay' },
    { key: 'week', value: rate.per_week, label: 'watchStats.rateWeek' },
    { key: 'month', value: rate.per_month, label: 'watchStats.rateMonth' },
  ].map((item) => ({
    key: item.key,
    value: formatRate(item.value, locale.value),
    label: t(item.label),
  }))
})

const trend = computed(() => trendDisplay(stats.value?.trend?.direction))

const periodLines = computed(() => {
  const period = stats.value?.period
  if (!period) return []
  const lines = []
  if (period.bytes) {
    lines.push(
      t('watchStats.periodGrowth', { size: formatBytes(period.bytes) })
    )
  }
  if (period.linked) {
    lines.push(t('watchStats.periodLinked', { count: period.linked }))
  }
  if (period.initial) {
    lines.push(t('watchStats.periodInitial', { count: period.initial }))
  }
  if (period.unknown) {
    lines.push(t('watchStats.periodUnknown', { count: period.unknown }))
  }
  return lines
})

const bars = computed(() => {
  const series = stats.value?.series || []
  return sparkline(series).map((height, index) => ({
    x: index * 10,
    height: Math.max(2, height * 100),
    count: series[index],
  }))
})
const seriesLabel = computed(() => (stats.value?.series || []).join(', '))

const providerRows = computed(() =>
  providerBreakdown(stats.value?.providers).map((row) => {
    const key = providerLabelKey(row.id)
    return { ...row, label: key ? t(key) : row.id }
  })
)

const counts = computed(() => trackFilterCounts(tracks.value, days.value))
const filterChips = computed(() =>
  TRACK_FILTERS.filter(
    (id) => id === 'all' || counts.value[id] || filter.value === id
  ).map((id) => ({
    id,
    label: t(`watchStats.filter.${id}`, { count: days.value }),
    count: counts.value[id],
  }))
)
const shown = computed(() =>
  tracks.value.filter((track) =>
    matchesTrackFilter(track, filter.value, days.value)
  )
)
const selectedTracks = computed(() =>
  shown.value.filter((track) => selected.value.has(track.file))
)

async function loadTracks() {
  loading.value = true
  try {
    const res = await monitorAPI.getWatchTracks(watchId.value)
    watch.value = res.data.watch
    tracks.value = (res.data.tracks || []).map((row) => ({
      ...normalizeTrack(row),
      watch: row.watch,
    }))
    failures.value = res.data.failures || []
    missing.value = res.data.missing || 0
  } catch {
    watch.value = null
  } finally {
    loading.value = false
  }
}

let statsRequest = 0
async function loadStats() {
  const request = ++statsRequest
  statsError.value = false
  try {
    const res = await monitorAPI.getMonitorStats(days.value)
    if (request === statsRequest) data.value = res.data
  } catch {
    if (request === statsRequest) statsError.value = true
  }
}

async function check() {
  checking.value = true
  try {
    await monitorAPI.checkMonitoredPlaylist(watchId.value)
    ui.toast(t('monitor.checking', { name: watch.value.name }))
    setTimeout(() => {
      loadTracks()
      loadStats()
    }, 4000)
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    setTimeout(() => (checking.value = false), 4000)
  }
}

async function zipSelected() {
  zipping.value = true
  await actions.downloadZip(selectedTracks.value)
  zipping.value = false
}

async function deleteTracks(list) {
  await actions.remove(list)
}

// Deleted here or from a row's menu: off the list, and the numbers redone.
watchRef(library.forgotten, (files) => {
  const gone = new Set(files)
  if (!tracks.value.some((track) => gone.has(track.file))) return
  tracks.value = tracks.value.filter((track) => !gone.has(track.file))
  selected.value = new Set(
    [...selected.value].filter((file) => !gone.has(file))
  )
  loadStats()
})

watchRef(days, loadStats)
watchRef(watchId, () => {
  selected.value = new Set()
  filter.value = 'all'
  loadTracks()
  loadStats()
})
watchRef(filter, () => (selected.value = new Set()))

onMounted(() => {
  loadTracks()
  loadStats()
})
</script>
