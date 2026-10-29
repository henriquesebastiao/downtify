<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('monitor.title')" :subtitle="t('monitor.subtitle')">
      <UiButton
        v-if="enabledInTab.length"
        variant="ghost"
        icon="retry"
        :loading="checkingAll"
        @click="checkAll"
      >
        {{ t('monitor.checkAll') }}
      </UiButton>
    </PageHeader>

    <UiTabs :items="tabs" :model-value="tab" />

    <form
      ref="watchForm"
      class="flex flex-col gap-2 rounded-panel border border-line-2 bg-surface p-2 sm:flex-row sm:items-center"
      @submit.prevent="add"
    >
      <label
        class="flex h-11 min-w-0 flex-none items-center gap-3 px-3 sm:flex-1"
      >
        <AppIcon name="link" :size="18" class="text-faint" />
        <span class="sr-only">{{ copy.urlLabel }}</span>
        <input
          v-model="newUrl[tab]"
          type="url"
          :placeholder="copy.urlPlaceholder"
          class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
        />
      </label>
      <div class="flex gap-2 px-1 pb-1 sm:p-0">
        <UiSelect
          v-model="newInterval"
          :options="intervalOptions(t)"
          :label="t('monitor.interval')"
          icon="clock"
          class="flex-1 sm:flex-none"
        />
        <UiButton
          type="submit"
          variant="primary"
          :icon="tab === 'artist' ? 'user' : 'radar'"
          :loading="adding"
          :disabled="!newUrl[tab].trim()"
        >
          {{ copy.add }}
        </UiButton>
      </div>
    </form>
    <div
      v-if="tab === 'artist'"
      class="-mt-3 rounded-panel border border-line-2 bg-surface px-4 py-3"
    >
      <ReleaseFilters
        v-model:types="newReleaseTypes"
        v-model:new-only="newOnly"
      />
    </div>
    <p
      v-if="addError[tab]"
      class="-mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-danger"
      role="alert"
    >
      {{ addError[tab] }}
      <UiButton
        v-if="wrongKind"
        size="sm"
        variant="ghost"
        :icon-right="'chevron-right'"
        @click="moveToOtherTab"
      >
        {{
          wrongKind === 'artist'
            ? t('monitor.addUnderArtists')
            : t('monitor.addUnderPlaylists')
        }}
      </UiButton>
    </p>

    <p class="flex items-start gap-2 text-[13px] text-pretty text-muted">
      <AppIcon name="info" :size="16" class="mt-0.5 shrink-0" />{{
        copy.explainer
      }}
    </p>

    <div v-if="loading && !items.length" class="flex flex-col gap-2">
      <UiSkeleton v-for="n in 4" :key="n" class="h-[72px] !rounded-[12px]" />
    </div>

    <UiEmpty
      v-else-if="!inTab.length"
      :icon="tab === 'artist' ? 'user' : 'playlist'"
      :title="copy.emptyTitle"
      :body="copy.emptyBody"
    />

    <template v-else>
      <div
        class="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-panel border border-line-2 bg-surface px-4 py-3"
      >
        <template v-if="totals">
          <div v-for="total in totalItems" :key="total.key" class="min-w-0">
            <p
              class="text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
            >
              {{ total.label }}
            </p>
            <p class="tabular text-lg font-semibold">{{ total.value }}</p>
          </div>
        </template>
        <p v-else-if="statsError" class="text-[13px] text-danger" role="alert">
          {{ t('watchStats.statsFailed') }}
        </p>
        <UiSkeleton v-else class="h-11 w-64" />
        <UiSegmented
          v-model="days"
          :options="periodOptions"
          show-labels
          class="ml-auto"
          :aria-label="t('watchStats.period')"
        />
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <label
          class="flex h-10 w-full items-center gap-2.5 rounded-control border border-line-2 bg-surface px-3 transition-colors focus-within:border-accent sm:w-72"
        >
          <AppIcon name="filter" :size="16" class="text-faint" />
          <span class="sr-only">{{ t('monitor.searchPlaceholder') }}</span>
          <input
            v-model="query"
            type="search"
            :placeholder="t('monitor.searchPlaceholder')"
            class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
          />
        </label>
        <UiChips v-model="show" :items="showFilters" />
        <div class="ml-auto flex items-center gap-2">
          <span class="hidden lg:inline-flex">
            <UiMenu :items="tableColumnMenu" :label="t('monitor.tableColumns')"
              ><template #trigger
                ><UiButton size="sm" variant="ghost" icon="filter">{{
                  t('monitor.tableColumns')
                }}</UiButton></template
              ></UiMenu
            >
          </span>
          <UiSelect
            v-model="sortKey"
            :options="sortOptions"
            :label="t('library.sortBy')"
            icon="sort"
          />
          <UiIconButton
            :icon="sortDir === 'asc' ? 'chevron-up' : 'chevron-down'"
            :label="
              sortDir === 'asc'
                ? t('monitor.ascending')
                : t('monitor.descending')
            "
            @click="sortDir = sortDir === 'asc' ? 'desc' : 'asc'"
          />
        </div>
      </div>

      <UiEmpty
        v-if="!visible.length"
        icon="filter"
        :title="t('library.noMatches')"
        :body="t('library.noMatchesHint')"
      >
        <UiButton variant="secondary" @click="clearFilters">
          {{ t('library.clearFilters') }}
        </UiButton>
      </UiEmpty>

      <template v-else>
        <div
          class="monitor-table-scroll rounded-panel focus-visible:outline-accent"
          tabindex="0"
          role="region"
          :aria-label="
            tab === 'artist' ? t('monitor.colArtist') : t('monitor.colPlaylist')
          "
          :style="tableStyle"
          :class="resizingTable ? 'select-none cursor-col-resize' : ''"
        >
          <div
            class="monitor-table-grid hidden items-center gap-4 border-b border-line px-4 pb-2.5 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase lg:grid"
          >
            <div
              v-for="column in tableColumns"
              :key="column.key"
              class="relative min-w-0 py-1"
            >
              <span :class="column.key === 'actions' ? 'sr-only' : ''">{{
                column.label
              }}</span>
              <div
                v-if="column.key !== 'actions'"
                role="separator"
                aria-orientation="vertical"
                tabindex="0"
                :aria-label="`${t('finder.resizeColumn')}: ${column.label}`"
                :title="t('finder.resizeHint')"
                :aria-valuemin="column.min"
                :aria-valuemax="column.max"
                :aria-valuenow="layout.widths[column.key]"
                class="absolute inset-y-0 -right-2 flex w-3 cursor-col-resize touch-none items-stretch justify-center outline-none group"
                @pointerdown="startTableResize(column.key, $event)"
                @dblclick="resetTableColumn(column.key)"
                @keydown.left.prevent="
                  nudgeTableColumn(column.key, $event.shiftKey ? -40 : -16)
                "
                @keydown.right.prevent="
                  nudgeTableColumn(column.key, $event.shiftKey ? 40 : 16)
                "
                @keydown.home.prevent="resetTableColumn(column.key)"
              >
                <span
                  class="w-0.5 bg-line-2 group-hover:bg-accent group-focus-visible:bg-accent"
                />
              </div>
            </div>
          </div>

          <TransitionGroup name="list" tag="ul" class="-mt-3 flex flex-col">
            <li
              v-for="item in visible"
              :key="item.id"
              class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-[12px] px-4 py-3 transition-colors hover:bg-surface monitor-table-grid"
            >
              <div
                class="flex min-w-0 items-center gap-3 transition-opacity"
                :class="item.enabled ? '' : 'opacity-50'"
              >
                <CoverArt
                  :src="tab === 'artist' ? artistCover(item) : ''"
                  :name="item.name"
                  :round="tab === 'artist'"
                  :icon="tab === 'artist' ? 'user' : 'playlist'"
                  rounded="rounded-[8px]"
                  :letter-size="16"
                  class="size-11"
                />
                <div class="min-w-0">
                  <button
                    type="button"
                    class="block max-w-full whitespace-normal break-words text-left text-sm font-semibold hover:underline"
                    :title="item.name"
                    @click="editing = item"
                  >
                    {{ item.name }}
                  </button>
                  <a
                    :href="item.url"
                    target="_blank"
                    rel="noopener"
                    :title="item.url"
                    class="block truncate font-mono text-[11.5px] text-muted hover:text-fg hover:underline"
                    >{{ displayUrl(item.url) }}</a
                  >
                  <span
                    v-if="
                      releaseFilterSummary(item).types.length ||
                      releaseFilterSummary(item).newOnly
                    "
                    class="mt-1 flex flex-wrap gap-1"
                  >
                    <UiBadge v-if="releaseFilterSummary(item).types.length">
                      {{
                        releaseFilterSummary(item)
                          .types.map((type) => t(`monitor.release.${type}`))
                          .join(' · ')
                      }}
                    </UiBadge>
                    <UiBadge
                      v-if="releaseFilterSummary(item).newOnly"
                      tone="accent"
                    >
                      {{ t('monitor.newOnlyBadge') }}
                    </UiBadge>
                  </span>
                </div>
              </div>

              <div class="flex items-center justify-end gap-1 lg:order-last">
                <UiIconButton
                  icon="retry"
                  :label="t('monitor.checkNow')"
                  size="sm"
                  :disabled="checking.has(item.id)"
                  :class="checking.has(item.id) ? 'animate-spin' : ''"
                  @click="check(item)"
                />
                <UiIconButton
                  icon="pencil"
                  :label="t('monitor.edit')"
                  size="sm"
                  @click="editing = item"
                />
                <UiMenu
                  :items="menuFor(item)"
                  :label="t('common.more')"
                  size="sm"
                />
              </div>

              <div
                class="col-span-2 flex flex-wrap items-center gap-2 lg:contents"
              >
                <span
                  class="lg:block"
                  :class="
                    layout.hidden.includes('source')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                >
                  <WatchSourceBadge :source="item.source" />
                </span>
                <UiSelect
                  :class="
                    layout.hidden.includes('checks')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                  :model-value="item.interval_minutes"
                  :options="intervalOptions(t, item.interval_minutes)"
                  :label="t('monitor.interval')"
                  size="sm"
                  @update:model-value="
                    (value) => update(item, { interval_minutes: value })
                  "
                />
                <span
                  class="flex items-center gap-1.5 text-[13px] text-muted"
                  :class="
                    layout.hidden.includes('checked')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                >
                  <AppIcon name="clock" :size="14" class="lg:hidden" />
                  {{
                    item.last_checked
                      ? timeAgo(item.last_checked, locale)
                      : t('monitor.never')
                  }}
                </span>
                <span
                  class="tabular text-[13px] text-muted"
                  :class="
                    layout.hidden.includes('size')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                >
                  {{
                    tab === 'artist'
                      ? t('monitor.releases', { count: item.last_track_count })
                      : t('common.tracks', { count: item.last_track_count })
                  }}
                </span>
                <RouterLink
                  :to="watchRouteFor(item)"
                  class="flex min-w-0 items-center gap-2 text-[13px] text-muted hover:text-fg"
                  :class="
                    layout.hidden.includes('activity')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                  :title="activityTitle(item)"
                >
                  <template v-if="stats.get(item.id)">
                    <AppIcon
                      :name="
                        trendDisplay(stats.get(item.id).trend.direction).icon
                      "
                      :size="14"
                      :class="[
                        trendDisplay(stats.get(item.id).trend.direction).flip
                          ? '-scale-y-100'
                          : '',
                        stats.get(item.id).trend.direction === 'up'
                          ? 'text-accent'
                          : '',
                      ]"
                    />
                    <span class="tabular font-semibold text-fg"
                      >+{{ stats.get(item.id).period.added }}</span
                    >
                    <span class="tabular truncate">{{
                      t('watchStats.rateWeekShort', {
                        rate: formatRate(
                          stats.get(item.id).rate.per_week,
                          locale
                        ),
                      })
                    }}</span>
                    <svg
                      v-if="stats.get(item.id).series.length > 1"
                      class="hidden h-4 w-12 shrink-0 text-accent xl:block"
                      :viewBox="`0 0 ${stats.get(item.id).series.length * 4} 16`"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                    >
                      <rect
                        v-for="(height, index) in sparkline(
                          stats.get(item.id).series
                        )"
                        :key="index"
                        :x="index * 4 + 0.5"
                        :y="16 - Math.max(1, height * 16)"
                        width="3"
                        :height="Math.max(1, height * 16)"
                        fill="currentColor"
                        :opacity="height ? 1 : 0.25"
                      />
                    </svg>
                  </template>
                  <span v-else class="text-faint">—</span>
                </RouterLink>
                <span
                  class="tabular truncate text-[13px] text-muted"
                  :class="
                    layout.hidden.includes('storage')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                  :title="storageTitle(item)"
                >
                  <template v-if="stats.get(item.id)">
                    {{ formatBytes(stats.get(item.id).storage.unique_bytes) }}
                    <span
                      v-if="stats.get(item.id).storage.shared_files"
                      class="text-faint"
                      >{{
                        t('watchStats.sharedShort', {
                          count: stats.get(item.id).storage.shared_files,
                        })
                      }}</span
                    >
                  </template>
                  <span v-else class="text-faint">—</span>
                </span>
                <UiSwitch
                  :model-value="item.enabled"
                  class="ml-auto lg:ml-0"
                  :class="
                    layout.hidden.includes('active')
                      ? 'monitor-column-hidden'
                      : ''
                  "
                  :aria-label="`${t('monitor.colActive')}: ${item.name}`"
                  @update:model-value="
                    (value) => update(item, { enabled: value })
                  "
                />
              </div>
            </li>
          </TransitionGroup>
        </div>
      </template>
    </template>

    <ArtistSuggestions
      v-if="tab === 'artist' && listed"
      :revision="watchesRevision"
      :busy="adding"
      :follow-error="addError.artist"
      @select="chooseSuggestedArtist"
    />

    <WatchEditDialog
      :watch="editing"
      :cover="editing && tab === 'artist' ? artistCover(editing) : ''"
      @close="editing = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import ReleaseFilters from '/src/components/monitor/ReleaseFilters.vue'
import ArtistSuggestions from '/src/components/monitor/ArtistSuggestions.vue'
import WatchEditDialog from '/src/components/monitor/WatchEditDialog.vue'
import WatchSourceBadge from '/src/components/monitor/WatchSourceBadge.vue'
import { intervalOptions } from '/src/components/monitor/intervals'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import { useUi } from '/src/model/ui'
import { artistPhotoSource } from '/src/lib/artistPhotoProxy'
import { formatBytes, timeAgo } from '/src/lib/format'
import {
  STAT_PERIODS,
  formatRate,
  sparkline,
  statsById,
  trendDisplay,
  watchRouteFor,
} from '/src/lib/watchStats'
import {
  WATCH_SORT_KEYS,
  countWatches,
  filterWatches,
  sortWatches,
  RELEASE_TYPES,
  releaseFilterSummary,
  watchKind,
  watchKindOfUrl,
} from '/src/lib/watches'
import { useI18n } from '/src/i18n'
import {
  MONITOR_COLUMNS,
  monitorLayout,
  resizeMonitorColumn,
  toggleMonitorColumn,
} from '/src/lib/monitorColumns'

const { t, locale } = useI18n()
const ui = useUi()
const route = useRoute()
const router = useRouter()

const items = ref([])
const watchForm = ref(null)
const loading = ref(false)
// The watches have been listed once (the suggestions wait for it, and stay
// mounted when the list is loaded again).
const listed = ref(false)
const adding = ref(false)
// Per tab, so switching tabs keeps what was typed in each.
const newUrl = reactive({ playlist: '', artist: '' })
const addError = reactive({ playlist: '', artist: '' })
const wrongKind = ref(null)
const newInterval = ref(360)
// A new artist watch's filters (the artists tab's form).
const newReleaseTypes = ref([...RELEASE_TYPES])
const newOnly = ref(false)
const checking = ref(new Set())
const checkingAll = ref(false)
const query = ref('')
const show = ref('all')
const editing = ref(null)
const sortKey = useLocalStorage('downtify-monitor-sort', 'created_at')
const sortDir = useLocalStorage('downtify-monitor-sort-dir', 'desc')
if (!WATCH_SORT_KEYS.includes(sortKey.value)) sortKey.value = 'created_at'

// What each watch holds and adds (GET /api/monitor/stats), over the
// period picked here (shared with a watch's own page).
const days = useLocalStorage('downtify-monitor-period', 30)
if (!STAT_PERIODS.includes(days.value)) days.value = 30
const stats = ref(new Map())
const totals = ref(null)
const statsError = ref(false)
let statsRequest = 0

async function loadStats() {
  const request = ++statsRequest
  statsError.value = false
  try {
    const res = await monitorAPI.getMonitorStats(days.value)
    if (request !== statsRequest) return
    stats.value = statsById(res.data)
    totals.value = res.data?.totals || null
  } catch {
    if (request === statsRequest) statsError.value = true
  }
}

watch(days, loadStats)

const periodOptions = computed(() =>
  STAT_PERIODS.map((value) => ({
    value,
    label: t('watchStats.days', { count: value }),
  }))
)

const totalItems = computed(() => {
  const added = inTab.value.reduce(
    (sum, item) => sum + (stats.value.get(item.id)?.period.added || 0),
    0
  )
  return [
    {
      key: 'new',
      label: t('watchStats.totalNew', { count: days.value }),
      value: added,
    },
    {
      key: 'songs',
      label: t('watchStats.totalSongs'),
      value: totals.value.files,
    },
    {
      key: 'size',
      label: t('watchStats.totalSize'),
      value: formatBytes(totals.value.bytes),
    },
    {
      key: 'shared',
      label: t('watchStats.totalShared'),
      value: totals.value.shared_files,
    },
  ]
})

function activityTitle(item) {
  const row = stats.value.get(item.id)
  if (!row) return ''
  return t('watchStats.activityTooltip', {
    added: row.period.added,
    count: days.value,
    rate: formatRate(row.rate.per_week, locale.value),
    trend: t(trendDisplay(row.trend.direction).label),
  })
}

function storageTitle(item) {
  const row = stats.value.get(item.id)
  if (!row) return ''
  return t('watchStats.storageTooltip', {
    unique: formatBytes(row.storage.unique_bytes),
    shared: formatBytes(row.storage.shared_bytes),
  })
}

const counts = computed(() => countWatches(items.value))

// /monitor/playlists and /monitor/artists; plain /monitor opens the tab
// that has something in it.
const tab = computed(() => {
  if (route.params.tab === 'artists') return 'artist'
  if (route.params.tab === 'playlists') return 'playlist'
  return !counts.value.playlist && counts.value.artist ? 'artist' : 'playlist'
})

// A drag updates only the grid at animation-frame cadence. Save once on
// release, not on every pointer move; resizing performs no API requests.
const savedTableLayouts = useLocalStorage(
  'downtify-monitor-table-layout-v1',
  {}
)
const dragLayout = ref(null)
const resizingTable = ref(false)
let stopTableResize = null
const layout = computed(() =>
  monitorLayout(dragLayout.value || savedTableLayouts.value?.[tab.value])
)
const tableColumns = computed(() =>
  MONITOR_COLUMNS.filter((col) => !layout.value.hidden.includes(col.key)).map(
    (col) => ({
      ...col,
      label:
        col.key === 'name'
          ? tab.value === 'artist'
            ? t('monitor.colArtist')
            : t('monitor.colPlaylist')
          : t(col.label),
    })
  )
)
const tableStyle = computed(() => ({
  '--monitor-columns': tableColumns.value
    .map((col) => `${layout.value.widths[col.key]}px`)
    .join(' '),
  '--monitor-width': `${tableColumns.value.reduce((sum, col) => sum + layout.value.widths[col.key], 32 + 16 * (tableColumns.value.length - 1))}px`,
}))
function saveTableLayout(value) {
  savedTableLayouts.value = {
    ...(savedTableLayouts.value || {}),
    [tab.value]: value,
  }
}
const tableColumnMenu = computed(() => [
  ...MONITOR_COLUMNS.slice(1, -1).map((col) => ({
    label: t(col.label),
    checked: !layout.value.hidden.includes(col.key),
    action: () => saveTableLayout(toggleMonitorColumn(layout.value, col.key)),
  })),
  { divider: true },
  {
    label: t('monitor.resetTableColumns'),
    icon: 'retry',
    action: () => saveTableLayout(monitorLayout({})),
  },
])
function nudgeTableColumn(key, delta) {
  saveTableLayout(
    resizeMonitorColumn(layout.value, key, layout.value.widths[key] + delta)
  )
}
function resetTableColumn(key) {
  saveTableLayout(
    resizeMonitorColumn(
      layout.value,
      key,
      MONITOR_COLUMNS.find((col) => col.key === key).width
    )
  )
}
function startTableResize(key, event) {
  if (event.button !== 0) return
  stopTableResize?.(false)
  event.preventDefault()
  const grip = event.currentTarget
  const from = monitorLayout(layout.value)
  const startX = event.clientX
  let latestX = startX
  let frame = null
  resizingTable.value = true
  grip.setPointerCapture(event.pointerId)
  const apply = () => {
    frame = null
    dragLayout.value = resizeMonitorColumn(
      from,
      key,
      from.widths[key] + latestX - startX
    )
  }
  const move = (e) => {
    if (e.pointerId !== event.pointerId) return
    latestX = e.clientX
    if (frame === null) frame = requestAnimationFrame(apply)
  }
  const finish = (commit) => {
    if (frame !== null) {
      cancelAnimationFrame(frame)
      apply()
    }
    if (commit && dragLayout.value) saveTableLayout(dragLayout.value)
    window.removeEventListener('pointermove', move, true)
    window.removeEventListener('pointerup', up, true)
    window.removeEventListener('pointercancel', cancel, true)
    if (grip.hasPointerCapture(event.pointerId))
      grip.releasePointerCapture(event.pointerId)
    resizingTable.value = false
    dragLayout.value = null
    stopTableResize = null
  }
  const up = (e) => {
    if (e.pointerId === event.pointerId) finish(true)
  }
  const cancel = (e) => {
    if (e.pointerId === event.pointerId) finish(false)
  }
  stopTableResize = finish
  window.addEventListener('pointermove', move, true)
  window.addEventListener('pointerup', up, true)
  window.addEventListener('pointercancel', cancel, true)
}
watch(tab, () => stopTableResize?.(false))
onBeforeUnmount(() => stopTableResize?.(false))

// Photos saved for the watched artists via the artist page's picker (see
// artist_profile.py), asked for in one call whenever the artists tab opens or
// its list changes. An artist is in here once the lookup has answered for
// them: only then does one with no saved photo get the display-only photo
// from the proxy (see lib/artistPhotoProxy.js) - and if the lookup fails,
// they keep the initials, as before.
const artistPhotos = ref({})
const artistNames = computed(() =>
  items.value.filter((i) => watchKind(i) === 'artist').map((i) => i.name)
)
let photosRequest = 0
watch(
  () => [tab.value, artistNames.value.join('\n')],
  async ([currentTab]) => {
    if (currentTab !== 'artist' || !artistNames.value.length) return
    const request = ++photosRequest
    try {
      const res = await API.getArtistArtBulk(artistNames.value)
      if (request === photosRequest) {
        artistPhotos.value = { ...artistPhotos.value, ...(res.data || {}) }
      }
    } catch {
      // No saved photos known: those artists keep their initials.
    }
  },
  { immediate: true }
)

function artistCover(item) {
  const entry = artistPhotos.value[item.name]
  return artistPhotoSource(item.name, entry, entry !== undefined).cover
}

const tabs = computed(() => [
  {
    id: 'playlist',
    label: t('monitor.filterPlaylists'),
    count: counts.value.playlist,
    to: { name: 'Monitor', params: { tab: 'playlists' } },
  },
  {
    id: 'artist',
    label: t('monitor.filterArtists'),
    count: counts.value.artist,
    to: { name: 'Monitor', params: { tab: 'artists' } },
  },
])

// Wording that depends on the tab.
const copy = computed(() =>
  tab.value === 'artist'
    ? {
        urlLabel: t('monitor.urlLabelArtist'),
        urlPlaceholder: t('monitor.urlPlaceholderArtist'),
        add: t('monitor.watchArtist'),
        explainer: newOnly.value
          ? t('monitor.explainerArtistsNewOnly')
          : t('monitor.explainerArtists'),
        emptyTitle: t('monitor.emptyArtistsTitle'),
        emptyBody: t('monitor.emptyArtistsBody'),
      }
    : {
        urlLabel: t('monitor.urlLabelPlaylist'),
        urlPlaceholder: t('monitor.urlPlaceholderPlaylist'),
        add: t('monitor.watchPlaylist'),
        explainer: t('monitor.explainerPlaylists'),
        emptyTitle: t('monitor.emptyPlaylistsTitle'),
        emptyBody: t('monitor.emptyPlaylistsBody'),
      }
)

const inTab = computed(() => filterWatches(items.value, { kind: tab.value }))
const enabledInTab = computed(() => inTab.value.filter((i) => i.enabled))

const showFilters = computed(() => {
  const paused = inTab.value.filter((i) => !i.enabled).length
  return [
    { id: 'all', label: t('monitor.filterAll'), count: inTab.value.length },
    { id: 'paused', label: t('monitor.filterPaused'), count: paused },
  ].filter((item) => item.id === 'all' || item.count || show.value === item.id)
})

const visible = computed(() =>
  sortWatches(
    filterWatches(items.value, {
      kind: tab.value,
      query: query.value,
      paused: show.value === 'paused',
    }),
    sortKey.value,
    sortDir.value,
    stats.value
  )
)

const sortOptions = computed(() => [
  { value: 'created_at', label: t('monitor.sortAdded') },
  { value: 'name', label: t('monitor.sortName') },
  { value: 'last_checked', label: t('monitor.sortChecked') },
  { value: 'interval_minutes', label: t('monitor.sortInterval') },
  {
    value: 'last_track_count',
    label:
      tab.value === 'artist'
        ? t('monitor.sortReleases')
        : t('monitor.sortSize'),
  },
  { value: 'activity', label: t('watchStats.sortActivity') },
  { value: 'rate', label: t('watchStats.sortRate') },
  { value: 'growth', label: t('watchStats.sortGrowth') },
  { value: 'storage', label: t('watchStats.sortStorage') },
  { value: 'contributed', label: t('watchStats.sortContributed') },
])

watch(tab, () => {
  query.value = ''
  show.value = 'all'
  wrongKind.value = null
})

function clearFilters() {
  query.value = ''
  show.value = 'all'
}

/** open.spotify.com/playlist/… without the scheme and tracking query. */
function displayUrl(url) {
  try {
    const parsed = new URL(url)
    parsed.searchParams.delete('si')
    const search = parsed.searchParams.toString()
    return `${parsed.host}${parsed.pathname}${search ? `?${search}` : ''}`
  } catch {
    return url
  }
}

async function load() {
  loading.value = true
  try {
    const res = await monitorAPI.listMonitoredPlaylists()
    items.value = res.data || []
  } finally {
    loading.value = false
    listed.value = true
  }
  loadStats()
}

// What the artist suggestions leave out: they load again when it changes.
const watchesRevision = computed(() =>
  JSON.stringify(items.value.map((item) => [item.id, item.name, item.kind]))
)

function tabRoute(kind) {
  return {
    name: 'Monitor',
    params: { tab: kind === 'artist' ? 'artists' : 'playlists' },
  }
}

async function add() {
  const kind = tab.value
  const url = newUrl[kind].trim()
  addError[kind] = ''
  wrongKind.value = null
  const detected = watchKindOfUrl(url)
  if (detected && detected !== kind) {
    addError[kind] =
      detected === 'artist'
        ? t('monitor.isArtistLink')
        : t('monitor.isPlaylistLink')
    wrongKind.value = detected
    return
  }
  adding.value = true
  try {
    const res = await monitorAPI.addMonitoredPlaylist(
      url,
      newInterval.value,
      kind === 'artist'
        ? { release_types: newReleaseTypes.value, new_only: newOnly.value }
        : {}
    )
    items.value = [res.data, ...items.value]
    newUrl[kind] = ''
    ui.toast(t('toast.watching', { name: res.data.name }), { kind: 'success' })
    // A link the page couldn't classify turned out to be the other kind.
    if (watchKind(res.data) !== kind) router.push(tabRoute(watchKind(res.data)))
  } catch (err) {
    addError[kind] = err?.response?.data?.detail || t('monitor.addFailed')
  } finally {
    adding.value = false
  }
}

// A suggested artist picked under the list (ArtistSuggestions), followed
// through the link box as a pasted link would be. "Paste a link", or a
// follow straight from the list that failed, brings the link box into view
// instead (its error shows there; the dialog shows its own).
async function chooseSuggestedArtist(artist) {
  if (adding.value) return
  if (artist.url) {
    newUrl.artist = artist.url
    await add()
    if (!addError.artist || artist.fromDialog) return
  }
  await nextTick()
  watchForm.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  watchForm.value?.querySelector('input')?.focus({ preventScroll: true })
}

function moveToOtherTab() {
  const target = wrongKind.value
  const from = tab.value
  newUrl[target] = newUrl[from]
  newUrl[from] = ''
  addError[from] = ''
  wrongKind.value = null
  router.push(tabRoute(target))
}

async function update(item, changes) {
  const before = { ...item }
  Object.assign(item, changes)
  try {
    const res = await monitorAPI.updateMonitoredPlaylist(item.id, changes)
    Object.assign(item, res.data)
  } catch {
    Object.assign(item, before)
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

function onSaved(updated) {
  const item = items.value.find((i) => i.id === updated.id)
  if (item) Object.assign(item, updated)
  // A retargeted watch downloads again: refresh its counts shortly.
  setTimeout(load, 4000)
}

async function check(item) {
  checking.value = new Set([...checking.value, item.id])
  try {
    await monitorAPI.checkMonitoredPlaylist(item.id)
    ui.toast(t('monitor.checking', { name: item.name }))
    setTimeout(load, 4000)
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  } finally {
    setTimeout(() => {
      const next = new Set(checking.value)
      next.delete(item.id)
      checking.value = next
    }, 4000)
  }
}

async function checkAll() {
  checkingAll.value = true
  const kind = tab.value
  for (const item of enabledInTab.value) {
    await monitorAPI.checkMonitoredPlaylist(item.id).catch(() => {})
  }
  ui.toast(
    kind === 'artist'
      ? t('monitor.checkingAllArtists')
      : t('monitor.checkingAllPlaylists')
  )
  setTimeout(() => {
    checkingAll.value = false
    load()
  }, 4000)
}

async function copyLink(item) {
  try {
    await navigator.clipboard.writeText(item.url)
    ui.toast(t('monitor.linkCopied'), { kind: 'success' })
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

async function remove(item) {
  const ok = await ui.confirm({
    title: t('confirm.stopWatchingTitle', { name: item.name }),
    body: t('confirm.stopWatchingBody'),
    confirmLabel: t('monitor.stop'),
    danger: true,
  })
  if (!ok) return
  try {
    await monitorAPI.deleteMonitoredPlaylist(item.id)
    items.value = items.value.filter((i) => i.id !== item.id)
  } catch {
    ui.toast(t('toast.actionFailed'), { kind: 'error' })
  }
}

function menuFor(item) {
  return [
    {
      label: t('monitor.edit'),
      icon: 'pencil',
      action: () => (editing.value = item),
    },
    {
      label: t('watchStats.details'),
      icon: 'activity',
      action: () => router.push(watchRouteFor(item)),
    },
    {
      label: item.enabled ? t('monitor.pause') : t('monitor.resume'),
      icon: item.enabled ? 'pause' : 'play',
      action: () => update(item, { enabled: !item.enabled }),
    },
    {
      label: t('monitor.copyLink'),
      icon: 'copy',
      action: () => copyLink(item),
    },
    {
      label: t('monitor.openSource'),
      icon: 'arrow-up-right',
      action: () => window.open(item.url, '_blank', 'noopener'),
    },
    { divider: true },
    {
      label: t('monitor.stop'),
      icon: 'trash',
      danger: true,
      action: () => remove(item),
    },
  ]
}

onMounted(load)
</script>

<style scoped>
@media (min-width: 1024px) {
  .monitor-table-scroll {
    overflow-x: auto;
  }
  .monitor-table-grid {
    grid-template-columns: var(--monitor-columns);
    min-width: var(--monitor-width);
  }
  .monitor-column-hidden {
    display: none !important;
  }
}
</style>
