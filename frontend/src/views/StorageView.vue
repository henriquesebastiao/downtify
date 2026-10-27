<template>
  <div
    class="mx-auto flex max-w-[1280px] flex-col gap-6 px-4 pt-6 pb-10 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('usage.title')" :subtitle="t('usage.subtitle')">
      <UiButton variant="ghost" icon="library" :to="{ name: 'Library' }">
        {{ t('library.backToLibrary') }}
      </UiButton>
      <UiButton
        v-if="auth.isAdmin.value"
        variant="ghost"
        icon="refresh"
        :loading="loading || scanning"
        @click="reload"
      >
        <span class="max-sm:sr-only">{{ t('common.refresh') }}</span>
      </UiButton>
    </PageHeader>

    <UiEmpty
      v-if="!auth.isAdmin.value"
      icon="lock"
      :title="t('usage.adminOnly')"
      :body="t('usage.adminOnlyHint')"
    />

    <template v-else>
      <UiSegmented
        v-model="days"
        :options="periodOptions"
        show-labels
        class="w-fit"
      />

      <p v-if="error" class="text-[13px] text-danger" role="alert">
        {{ t('usage.loadFailed') }}
      </p>

      <div
        v-if="!report && loading"
        class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6"
      >
        <UiSkeleton v-for="n in 6" :key="n" class="h-[84px] !rounded-panel" />
      </div>

      <template v-if="report">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
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
            <p
              class="tabular mt-1 truncate text-xl font-semibold"
              :class="tile.tone"
            >
              {{ tile.value }}
            </p>
            <p
              v-if="tile.hint"
              class="mt-0.5 text-[12px] text-pretty text-muted"
            >
              {{ tile.hint }}
            </p>
          </div>
        </div>

        <!-- Library size over time -->
        <UiPanel
          :title="t('usage.growthTitle')"
          :description="t('usage.growthHint')"
        >
          <div
            class="relative mt-7 select-none"
            @pointermove="hoverAt"
            @pointerleave="hover = -1"
          >
            <svg
              class="block h-44 w-full overflow-visible"
              :viewBox="`0 0 ${CHART_W} ${CHART_H}`"
              preserveAspectRatio="none"
              role="img"
              :aria-label="t('usage.growthTitle')"
            >
              <line
                v-for="y in [0, CHART_H / 2, CHART_H]"
                :key="y"
                x1="0"
                :x2="CHART_W"
                :y1="y"
                :y2="y"
                class="stroke-line-3"
                stroke-width="1"
                vector-effect="non-scaling-stroke"
              />
              <path :d="chart.area" class="fill-accent/10" />
              <path
                v-if="chart.estimated"
                :d="chart.estimated"
                fill="none"
                class="stroke-accent/60"
                stroke-width="2"
                stroke-dasharray="4 4"
                stroke-linejoin="round"
                vector-effect="non-scaling-stroke"
              />
              <path
                v-if="chart.measured"
                :d="chart.measured"
                fill="none"
                class="stroke-accent"
                stroke-width="2"
                stroke-linejoin="round"
                stroke-linecap="round"
                vector-effect="non-scaling-stroke"
              />
              <line
                v-if="hovered"
                :x1="hovered.x"
                :x2="hovered.x"
                y1="0"
                :y2="CHART_H"
                class="stroke-muted"
                stroke-width="1"
                vector-effect="non-scaling-stroke"
              />
            </svg>
            <span
              class="tabular pointer-events-none absolute top-0 left-1 -translate-y-full pb-1 text-[11px] text-faint"
              >{{ formatBytes(chart.max) }}</span
            >
            <span
              class="tabular pointer-events-none absolute bottom-0 left-1 translate-y-full pt-1 text-[11px] text-faint"
              >{{ formatBytes(chart.min) }}</span
            >
            <template v-if="hovered">
              <span
                class="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent ring-2 ring-surface"
                :style="{
                  left: `${(hovered.x / CHART_W) * 100}%`,
                  top: `${(hovered.y / CHART_H) * 100}%`,
                }"
              />
              <div
                class="pointer-events-none absolute top-2 z-10 min-w-36 rounded-control border border-line-3 bg-raised px-3 py-2 text-[12px] shadow-float"
                :style="tooltipStyle"
              >
                <p class="font-semibold text-fg">
                  {{ formatDay(hovered.point.day, locale) }}
                </p>
                <p class="tabular text-fg-2">
                  {{ formatBytes(hovered.point.bytes) }}
                </p>
                <p class="text-muted">
                  {{ t('usage.songs', { count: hovered.point.files }) }}
                </p>
                <p v-if="hovered.point.estimated" class="text-faint">
                  {{ t('usage.estimated') }}
                </p>
              </div>
            </template>
          </div>
          <div class="mt-6 flex justify-between text-[11px] text-faint">
            <span>{{ formatDay(firstDay, locale) }}</span>
            <span>{{ formatDay(lastDay, locale) }}</span>
          </div>
          <p
            v-if="measuredSince"
            class="mt-3 flex items-start gap-2 text-[13px] text-muted"
          >
            <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />
            {{
              t('usage.estimatedNote', {
                date: formatDay(measuredSince, locale),
              })
            }}
          </p>
          <p
            v-else-if="allEstimated"
            class="mt-3 flex items-start gap-2 text-[13px] text-muted"
          >
            <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />
            {{ t('usage.allEstimatedNote') }}
          </p>
          <div class="sr-only">
            <table :aria-label="t('usage.growthTitle')">
              <tr v-for="point in report.growth.points" :key="point.day">
                <th scope="row">{{ point.day }}</th>
                <td>{{ formatBytes(point.bytes) }}</td>
                <td>{{ t('usage.songs', { count: point.files }) }}</td>
              </tr>
            </table>
          </div>

          <div class="mt-6 border-t border-line-2 pt-5">
            <p
              class="mb-2 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
            >
              {{
                report.period.bucket_days === 1
                  ? t('usage.addedPerDay')
                  : t('usage.addedPerWeek')
              }}
            </p>
            <svg
              class="h-20 w-full text-accent"
              :viewBox="`0 0 ${addedBars.length * 10} 100`"
              preserveAspectRatio="none"
              role="img"
              :aria-label="addedLabel"
            >
              <rect
                v-for="bar in addedBars"
                :key="bar.x"
                :x="bar.x + 1"
                :y="100 - bar.height"
                width="8"
                :height="bar.height"
                rx="1.5"
                fill="currentColor"
                :opacity="bar.files ? 1 : 0.18"
              >
                <title>{{ bar.title }}</title>
              </rect>
            </svg>
          </div>
        </UiPanel>

        <div class="grid gap-6 lg:grid-cols-2">
          <!-- Where the audio came from -->
          <UiPanel
            :title="t('usage.sourcesTitle')"
            :description="t('usage.sourcesHint', { count: days })"
          >
            <ul v-if="sources.length" class="flex flex-col gap-3.5">
              <li v-for="row in sources" :key="row.id" class="text-sm">
                <div class="flex items-baseline justify-between gap-3">
                  <span class="truncate font-medium">{{
                    providerName(row.id)
                  }}</span>
                  <span class="tabular shrink-0 text-muted">
                    {{ formatBytes(row.bytes) }} ·
                    {{ t('usage.songs', { count: row.files }) }}
                  </span>
                </div>
                <div
                  class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2"
                >
                  <div
                    class="h-full rounded-full bg-accent"
                    :style="{ width: `${Math.max(2, row.share * 100)}%` }"
                  />
                </div>
                <p v-if="row.added" class="tabular mt-1 text-[12px] text-muted">
                  {{
                    t('usage.addedInPeriod', {
                      size: formatBytes(row.added),
                      count: row.addedFiles,
                    })
                  }}
                </p>
              </li>
            </ul>
            <p v-else class="text-sm text-muted">
              {{ t('usage.emptyLibrary') }}
            </p>
          </UiPanel>

          <!-- Where it is, and in which format -->
          <UiPanel :title="t('usage.whereTitle')">
            <div class="flex flex-col gap-6">
              <div v-for="group in whereGroups" :key="group.key">
                <p
                  class="mb-2 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
                >
                  {{ group.label }}
                </p>
                <ul class="flex flex-col gap-3">
                  <li v-for="row in group.rows" :key="row.id" class="text-sm">
                    <div class="flex items-baseline justify-between gap-3">
                      <span class="truncate">{{ row.label }}</span>
                      <span class="tabular shrink-0 text-muted">
                        {{ formatBytes(row.bytes) }} ·
                        {{ t('usage.songs', { count: row.files }) }}
                      </span>
                    </div>
                    <div
                      class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2"
                    >
                      <div
                        class="h-full rounded-full bg-accent"
                        :style="{ width: `${Math.max(2, row.share * 100)}%` }"
                      />
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </UiPanel>
        </div>

        <!-- Downloads -->
        <UiPanel
          :title="t('usage.downloadsTitle')"
          :description="t('usage.downloadsHint', { count: days })"
        >
          <div class="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <div class="flex min-w-0 flex-col gap-4">
              <div
                v-for="row in outcomeRows"
                :key="row.id"
                class="grid grid-cols-[7.5rem_minmax(0,1fr)] items-end gap-3"
              >
                <div class="min-w-0">
                  <p class="flex items-center gap-1.5 text-[13px] text-muted">
                    <AppIcon :name="row.icon" :size="14" :class="row.text" />
                    {{ row.label }}
                  </p>
                  <p class="tabular text-lg font-semibold">{{ row.total }}</p>
                </div>
                <svg
                  class="h-10 w-full"
                  :class="row.text"
                  :viewBox="`0 0 ${row.bars.length * 10} 100`"
                  preserveAspectRatio="none"
                  role="img"
                  :aria-label="`${row.label}: ${row.bars.map((b) => b.count).join(', ')}`"
                >
                  <rect
                    v-for="(bar, index) in row.bars"
                    :key="index"
                    :x="index * 10 + 1"
                    :y="100 - Math.max(3, bar.height * 100)"
                    width="8"
                    :height="Math.max(3, bar.height * 100)"
                    rx="1.5"
                    fill="currentColor"
                    :opacity="bar.count ? 1 : 0.15"
                  >
                    <title>{{ bar.count }}</title>
                  </rect>
                </svg>
              </div>
              <p class="text-[12px] text-faint">
                {{
                  report.downloads.bucket_days === 1
                    ? t('usage.perDay')
                    : t('usage.perWeek')
                }}
              </p>
            </div>
            <div class="min-w-0">
              <p
                class="mb-2 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
              >
                {{
                  t('usage.downloadedBySource', {
                    size: formatBytes(report.downloads.bytes),
                  })
                }}
              </p>
              <ul
                v-if="downloadSources.length"
                class="flex flex-col gap-3 text-sm"
              >
                <li v-for="row in downloadSources" :key="row.id">
                  <div class="flex items-baseline justify-between gap-3">
                    <span class="truncate">{{ providerName(row.id) }}</span>
                    <span class="tabular shrink-0 text-muted">
                      {{ formatBytes(row.bytes) }} ·
                      {{ t('usage.songs', { count: row.files }) }}
                    </span>
                  </div>
                  <div
                    class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2"
                  >
                    <div
                      class="h-full rounded-full bg-accent"
                      :style="{ width: `${Math.max(2, row.share * 100)}%` }"
                    />
                  </div>
                </li>
              </ul>
              <p v-else class="text-sm text-muted">
                {{ t('usage.noDownloads') }}
              </p>
            </div>
          </div>
          <p
            v-if="logNote"
            class="mt-4 flex items-start gap-2 text-[13px] text-muted"
          >
            <AppIcon name="info" :size="15" class="mt-0.5 shrink-0" />
            {{ logNote }}
          </p>
        </UiPanel>

        <!-- What could be cleaned up -->
        <UiPanel
          :title="t('usage.cleanupTitle')"
          :description="t('usage.cleanupHint')"
        >
          <div class="grid gap-3 sm:grid-cols-2">
            <details
              v-for="card in cleanupCards"
              :key="card.key"
              class="group min-w-0 rounded-control border border-line-2 bg-surface-2"
            >
              <summary
                class="flex cursor-pointer list-none items-start gap-3 p-3.5 [&::-webkit-details-marker]:hidden"
              >
                <AppIcon
                  :name="card.icon"
                  :size="18"
                  class="mt-0.5 shrink-0 text-muted"
                />
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-semibold">{{ card.title }}</p>
                  <p class="mt-0.5 text-[12.5px] text-pretty text-muted">
                    {{ card.hint }}
                  </p>
                </div>
                <div class="shrink-0 text-right">
                  <template v-if="card.part">
                    <p class="tabular text-sm font-semibold">
                      {{ formatBytes(card.part.bytes) }}
                    </p>
                    <p class="tabular text-[12px] text-muted">
                      {{ t('usage.files', { count: card.part.files }) }}
                    </p>
                  </template>
                  <UiSkeleton v-else class="h-9 w-16" />
                </div>
                <AppIcon
                  v-if="card.items.length"
                  name="chevron-down"
                  :size="16"
                  class="mt-0.5 shrink-0 text-faint transition-transform group-open:rotate-180"
                />
              </summary>
              <ul
                v-if="card.items.length"
                class="flex max-h-72 flex-col divide-y divide-line-2 overflow-y-auto border-t border-line-2 px-3.5"
              >
                <li
                  v-for="item in card.items"
                  :key="item.key"
                  class="flex flex-col gap-0.5 py-2 text-[12.5px]"
                >
                  <div class="flex items-baseline justify-between gap-3">
                    <span class="min-w-0 truncate font-medium">{{
                      item.title
                    }}</span>
                    <span class="tabular shrink-0 text-muted">{{
                      item.size
                    }}</span>
                  </div>
                  <span
                    v-for="line in item.lines"
                    :key="line"
                    class="truncate font-mono text-[11.5px] text-faint"
                    :title="line"
                    >{{ line }}</span
                  >
                </li>
              </ul>
            </details>
          </div>
          <p
            v-if="
              report.working.slskd_in_place &&
              !report.working.files &&
              hasSlskdSongs
            "
            class="mt-3 text-[12.5px] text-muted"
          >
            {{ t('usage.workingInPlace') }}
          </p>
        </UiPanel>

        <!-- Folders -->
        <UiPanel
          :title="t('usage.foldersTitle')"
          :description="t('usage.foldersHint')"
        >
          <template #actions>
            <UiButton
              variant="ghost"
              icon="refresh"
              :loading="scanning"
              @click="loadScan(true)"
            >
              <span class="max-sm:sr-only">{{ t('usage.rescan') }}</span>
            </UiButton>
          </template>
          <p v-if="scanError" class="text-[13px] text-danger" role="alert">
            {{ t('usage.scanFailed') }}
          </p>
          <div v-else-if="!scan" class="flex flex-col gap-3">
            <p class="text-[13px] text-muted">{{ t('usage.scanning') }}</p>
            <UiSkeleton class="h-24 w-full" />
          </div>
          <template v-else>
            <div class="grid gap-6 lg:grid-cols-2">
              <div v-for="folder in scanFolders" :key="folder.id">
                <div class="flex items-baseline justify-between gap-3">
                  <p class="text-sm font-semibold">
                    {{ t(`usage.folder.${folder.id}`) }}
                  </p>
                  <p class="tabular text-sm text-muted">
                    {{ formatBytes(folder.bytes) }}
                  </p>
                </div>
                <p
                  class="truncate font-mono text-[11.5px] text-faint"
                  :title="folder.path"
                >
                  {{ folder.path }}
                </p>
                <ul class="mt-3 flex flex-col gap-2.5 text-[13px]">
                  <li v-for="kind in folder.kinds" :key="kind.id">
                    <div class="flex items-baseline justify-between gap-3">
                      <span class="truncate">{{
                        t(`usage.kind.${kind.id}`)
                      }}</span>
                      <span class="tabular shrink-0 text-muted">
                        {{ formatBytes(kind.bytes) }} ·
                        {{ t('usage.files', { count: kind.files }) }}
                      </span>
                    </div>
                    <div
                      class="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2"
                    >
                      <div
                        class="h-full rounded-full"
                        :class="
                          kind.id === 'temporary' ? 'bg-warn' : 'bg-accent'
                        "
                        :style="{ width: `${Math.max(2, kind.share * 100)}%` }"
                      />
                    </div>
                  </li>
                </ul>
              </div>
            </div>
            <p class="mt-4 text-[12px] text-faint">
              {{
                t('usage.scannedAt', {
                  when: timeAgo(scan.scanned_at, locale),
                  seconds: scan.seconds,
                })
              }}
            </p>
          </template>
        </UiPanel>
      </template>
    </template>
  </div>
</template>

<script setup>
// Library storage and usage (admins): how big the library is and how
// fast it grows, which providers it came from, how downloads ended,
// and what could be cleaned up - duplicates, slskd's working copies,
// leftover temporary files and orphaned sidecars. Reads GET
// /api/library/usage and /api/library/usage/scan; deletes nothing.
import { computed, onMounted, ref, watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiPanel from '/src/components/ui/UiPanel.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import API from '/src/model/api'
import { useAuth } from '/src/model/auth'
import { formatBytes, timeAgo } from '/src/lib/format'
import {
  DOWNLOAD_OUTCOMES,
  FORECAST_MAX_DAYS,
  USAGE_PERIODS,
  breakdownRows,
  cleanupSummary,
  daysLeftTone,
  folderKinds,
  formatDay,
  growthChart,
  measuredFrom,
  nearestIndex,
  outcomeBars,
  providerRows,
} from '/src/lib/libraryUsage'
import { providerLabelKey, sparkline } from '/src/lib/watchStats'
import { useI18n } from '/src/i18n'

const CHART_W = 600
const CHART_H = 160
const TONE_TEXT = { danger: 'text-danger', warn: 'text-warn' }

const { t, locale } = useI18n()
const auth = useAuth()

const days = useLocalStorage('downtify-usage-period', 30)
if (!USAGE_PERIODS.includes(days.value)) days.value = 30

const report = ref(null)
const scan = ref(null)
const loading = ref(false)
const scanning = ref(false)
const error = ref(false)
const scanError = ref(false)
const hover = ref(-1)

const periodOptions = computed(() =>
  USAGE_PERIODS.map((value) => ({
    value,
    label: t('watchStats.days', { count: value }),
  }))
)

function providerName(id) {
  const key = providerLabelKey(id)
  return key ? t(key) : id
}

function signedBytes(bytes) {
  const value = Number(bytes) || 0
  if (!value) return formatBytes(0)
  return `${value > 0 ? '+' : '−'}${formatBytes(Math.abs(value))}`
}

const cleanup = computed(() => cleanupSummary(report.value, scan.value))
const hasSlskdSongs = computed(() =>
  (report.value?.library?.by_location || []).some((row) => row.id === 'slskd')
)

const tiles = computed(() => {
  const r = report.value
  if (!r) return []
  const disk = r.disk
  // Decades away says nothing useful; just the total, then.
  const daysLeft =
    disk?.days_left !== null && disk?.days_left <= FORECAST_MAX_DAYS
      ? disk.days_left
      : null
  const tone = daysLeftTone(daysLeft)
  const tiles = [
    {
      key: 'library',
      label: t('usage.tileLibrary'),
      value: formatBytes(r.library.bytes),
      hint: t('usage.songs', { count: r.library.files }),
    },
    {
      key: 'added',
      label: t('usage.tileAdded', { count: r.days }),
      value: signedBytes(r.period.bytes),
      hint: t('usage.songs', { count: r.period.files }),
      tone: r.period.bytes ? 'text-accent' : '',
    },
    {
      key: 'growth',
      label: t('usage.tileGrowth'),
      value: signedBytes(r.growth.change.bytes),
      hint: t('usage.perWeekRate', {
        size: signedBytes(r.growth.per_day_bytes * 7),
      }),
    },
  ]
  if (disk) {
    tiles.push({
      key: 'disk',
      label: t('usage.tileFree'),
      value: formatBytes(disk.free),
      hint:
        daysLeft === null
          ? t('usage.ofTotal', { total: formatBytes(disk.total) })
          : t('usage.daysLeft', {
              total: formatBytes(disk.total),
              count: daysLeft,
            }),
      tone: TONE_TEXT[tone] || '',
    })
  }
  tiles.push(
    {
      key: 'downloads',
      label: t('usage.tileDownloads'),
      value: r.downloads.completed,
      hint: t('usage.downloadsShort', {
        skipped: r.downloads.skipped,
        failed: r.downloads.failed,
      }),
    },
    {
      key: 'cleanup',
      label: t('usage.tileCleanup'),
      value: formatBytes(cleanup.value.total.bytes),
      hint: t('usage.files', { count: cleanup.value.total.files }),
      tone: cleanup.value.total.bytes ? 'text-warn' : '',
    }
  )
  return tiles
})

// ── Growth chart ─────────────────────────────────────────────────────────
const chart = computed(() =>
  growthChart(report.value?.growth?.points, {
    width: CHART_W,
    height: CHART_H,
  })
)
const hovered = computed(() => chart.value.coords[hover.value] || null)
const firstDay = computed(() => report.value?.growth?.points?.[0]?.day || '')
const lastDay = computed(() => report.value?.growth?.points?.at(-1)?.day || '')
const measuredSince = computed(() => measuredFrom(report.value?.growth?.points))
const allEstimated = computed(() => {
  const points = report.value?.growth?.points || []
  return points.length > 1 && points.slice(0, -1).every((p) => p.estimated)
})
const tooltipStyle = computed(() => {
  const left = (hovered.value.x / CHART_W) * 100
  return left > 60
    ? { right: `${100 - left}%`, marginRight: '12px' }
    : { left: `${left}%`, marginLeft: '12px' }
})

function hoverAt(event) {
  const box = event.currentTarget.getBoundingClientRect()
  if (!box.width) return
  hover.value = nearestIndex(
    (event.clientX - box.left) / box.width,
    chart.value.coords.length
  )
}

const addedBars = computed(() => {
  const series = report.value?.period?.series || []
  return sparkline(series.map((bucket) => bucket.bytes)).map(
    (height, index) => ({
      x: index * 10,
      height: Math.max(2, height * 100),
      files: series[index].files,
      title: `${formatBytes(series[index].bytes)} · ${t('usage.songs', {
        count: series[index].files,
      })}`,
    })
  )
})
const addedLabel = computed(() =>
  (report.value?.period?.series || [])
    .map((bucket) => formatBytes(bucket.bytes))
    .join(', ')
)

// ── Breakdowns ───────────────────────────────────────────────────────────
const sources = computed(() =>
  providerRows(report.value?.library, report.value?.period)
)
const whereGroups = computed(() => {
  const library = report.value?.library
  return [
    {
      key: 'location',
      label: t('usage.byLocation'),
      rows: breakdownRows(library?.by_location).map((row) => ({
        ...row,
        label: t(`usage.location.${row.id}`),
      })),
    },
    {
      key: 'format',
      label: t('usage.byFormat'),
      rows: breakdownRows(library?.by_format).map((row) => ({
        ...row,
        label: row.id === 'unknown' ? t('usage.unknown') : row.id.toUpperCase(),
      })),
    },
  ].filter((group) => group.rows.length)
})

// ── Downloads ────────────────────────────────────────────────────────────
const OUTCOME_LOOK = {
  completed: { icon: 'check-circle', text: 'text-accent' },
  skipped: { icon: 'minus', text: 'text-muted' },
  failed: { icon: 'alert', text: 'text-danger' },
}
const outcomeRows = computed(() => {
  const downloads = report.value?.downloads
  const bars = outcomeBars(downloads?.series)
  return DOWNLOAD_OUTCOMES.map((id) => ({
    id,
    label: t(`usage.outcome.${id}`),
    total: downloads?.[id] || 0,
    bars: bars[id],
    ...OUTCOME_LOOK[id],
  }))
})
const downloadSources = computed(() =>
  breakdownRows(report.value?.downloads?.by_provider)
)
const logNote = computed(() => {
  const r = report.value
  if (!r) return ''
  const since = r.downloads.since
  if (!since) return t('usage.logEmptyNote')
  const start = Date.now() - r.days * 86400000
  if (Date.parse(since) > start) {
    return t('usage.logSinceNote', {
      date: new Date(since).toLocaleDateString(locale.value),
    })
  }
  return ''
})

// ── Cleanup ──────────────────────────────────────────────────────────────
function fileItem(item) {
  const where = item.folder ? `${t(`usage.folder.${item.folder}`)} · ` : ''
  return {
    key: `${item.folder || ''}/${item.file}`,
    title: item.file.split('/').at(-1),
    size: formatBytes(item.bytes),
    lines: [`${where}${item.file}`],
  }
}

const cleanupCards = computed(() => {
  const r = report.value
  const parts = cleanup.value
  const duplicates = r?.duplicates
  return [
    {
      key: 'duplicates',
      icon: 'copy',
      title: t('usage.duplicatesTitle'),
      hint: duplicates
        ? t('usage.duplicatesHint', {
            exact: duplicates.exact.groups,
            likely: duplicates.likely.groups,
          })
        : '',
      part: parts.duplicates,
      items: (duplicates?.examples || []).map((group) => ({
        key: group.files.map((f) => f.file).join('|'),
        title: [group.artist, group.title].filter(Boolean).join(' – '),
        size: `${t(`usage.duplicateKind.${group.kind}`)} · ${formatBytes(
          group.bytes
        )}`,
        lines: group.files.map(
          (f) =>
            `${providerName(f.provider)} · ${formatBytes(f.bytes)} · ${f.file}`
        ),
      })),
    },
    {
      key: 'working',
      icon: 'folder',
      title: t('usage.workingTitle'),
      hint: t('usage.workingHint'),
      part: parts.working,
      items: (r?.working?.examples || []).map(fileItem),
    },
    {
      key: 'leftovers',
      icon: 'clock',
      title: t('usage.leftoversTitle'),
      hint: t('usage.leftoversHint'),
      part: parts.leftovers,
      items: (scan.value?.leftovers?.examples || []).map(fileItem),
    },
    {
      key: 'orphans',
      icon: 'file-music',
      title: t('usage.orphansTitle'),
      hint: t('usage.orphansHint'),
      part: parts.orphans,
      items: (scan.value?.orphans?.examples || []).map(fileItem),
    },
  ]
})

const scanFolders = computed(() =>
  (scan.value?.folders || []).map((folder) => ({
    ...folder,
    kinds: folderKinds(folder),
  }))
)

// ── Loading ──────────────────────────────────────────────────────────────
let request = 0
async function load() {
  if (!auth.isAdmin.value) return
  const mine = ++request
  loading.value = true
  error.value = false
  try {
    const res = await API.getLibraryUsage(days.value)
    if (mine === request) report.value = res.data
  } catch {
    if (mine === request) error.value = true
  } finally {
    if (mine === request) loading.value = false
  }
}

async function loadScan(refresh = false) {
  if (!auth.isAdmin.value || scanning.value) return
  scanning.value = true
  scanError.value = false
  try {
    const res = await API.scanLibraryUsage(refresh)
    scan.value = res.data
  } catch {
    scanError.value = true
  } finally {
    scanning.value = false
  }
}

function reload() {
  load()
  loadScan(true)
}

watch(days, load)
watch(
  () => auth.isAdmin.value,
  (admin) => {
    if (admin && !report.value) reload()
  }
)
onMounted(() => {
  load()
  loadScan()
})
</script>
