<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('monitor.title')" :subtitle="t('monitor.subtitle')">
      <UiButton
        v-if="items.length"
        variant="ghost"
        icon="retry"
        :loading="checkingAll"
        @click="checkAll"
      >
        {{ t('monitor.checkAll') }}
      </UiButton>
    </PageHeader>

    <form
      class="flex flex-col gap-2 rounded-panel border border-line-2 bg-surface p-2 sm:flex-row sm:items-center"
      @submit.prevent="add"
    >
      <label
        class="flex h-11 min-w-0 flex-none items-center gap-3 px-3 sm:flex-1"
      >
        <AppIcon name="link" :size="18" class="text-faint" />
        <span class="sr-only">{{ t('monitor.urlLabel') }}</span>
        <input
          v-model="newUrl"
          type="url"
          :placeholder="t('monitor.urlPlaceholder')"
          class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
        />
      </label>
      <div class="flex gap-2 px-1 pb-1 sm:p-0">
        <UiSelect
          v-model="newInterval"
          :options="intervalOptions"
          :label="t('monitor.interval')"
          icon="clock"
          class="flex-1 sm:flex-none"
        />
        <UiButton
          type="submit"
          variant="primary"
          icon="radar"
          :loading="adding"
          :disabled="!newUrl.trim()"
        >
          {{ t('monitor.watch') }}
        </UiButton>
      </div>
    </form>
    <p v-if="addError" class="-mt-3 text-[13px] text-danger">{{ addError }}</p>

    <p class="flex items-start gap-2 text-[13px] text-pretty text-muted">
      <AppIcon name="info" :size="16" class="mt-0.5 shrink-0" />{{
        t('monitor.explainer')
      }}
    </p>

    <div v-if="loading && !items.length" class="flex flex-col gap-2">
      <UiSkeleton v-for="n in 4" :key="n" class="h-[72px] !rounded-[12px]" />
    </div>

    <UiEmpty
      v-else-if="!items.length"
      icon="radar"
      :title="t('monitor.emptyTitle')"
      :body="t('monitor.emptyBody')"
    />

    <template v-else>
      <div class="flex flex-wrap items-center gap-2">
        <UiChips v-model="filter" :items="filters" />
        <div class="ml-auto flex items-center gap-2">
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

      <div
        class="hidden grid-cols-[minmax(0,2fr)_140px_170px_150px_110px_64px_96px] items-center gap-4 border-b border-line px-4 pb-2.5 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase lg:grid"
      >
        <span>{{ t('monitor.colWatching') }}</span>
        <span>{{ t('monitor.colSource') }}</span>
        <span>{{ t('monitor.colChecks') }}</span>
        <span>{{ t('monitor.colLastChecked') }}</span>
        <span>{{ t('monitor.colSize') }}</span>
        <span>{{ t('monitor.colActive') }}</span>
        <span />
      </div>

      <TransitionGroup name="list" tag="ul" class="-mt-3 flex flex-col">
        <li
          v-for="item in visible"
          :key="item.id"
          class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-[12px] px-4 py-3 transition-colors hover:bg-surface lg:grid-cols-[minmax(0,2fr)_140px_170px_150px_110px_64px_96px]"
        >
          <div
            class="flex min-w-0 items-center gap-3 transition-opacity"
            :class="item.enabled ? '' : 'opacity-50'"
          >
            <CoverArt
              :name="item.name"
              :round="item.kind === 'artist'"
              :icon="item.kind === 'artist' ? 'user' : 'playlist'"
              rounded="rounded-[8px]"
              :letter-size="16"
              class="size-11"
            />
            <div class="min-w-0">
              <a
                :href="item.url"
                target="_blank"
                rel="noopener"
                class="block truncate text-sm font-semibold hover:underline"
                >{{ item.name }}</a
              >
              <span class="text-xs text-muted">
                {{
                  item.kind === 'artist'
                    ? t('monitor.kindArtist')
                    : t('monitor.kindPlaylist')
                }}
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
            <UiMenu
              :items="menuFor(item)"
              :label="t('common.more')"
              size="sm"
            />
          </div>

          <div class="col-span-2 flex flex-wrap items-center gap-2 lg:contents">
            <span class="lg:block">
              <UiBadge
                v-if="item.source === 'youtube_music'"
                tone="neutral"
                icon="youtube"
                >YouTube Music</UiBadge
              >
              <UiBadge v-else tone="spotify" icon="spotify">Spotify</UiBadge>
            </span>
            <UiSelect
              :model-value="item.interval_minutes"
              :options="intervalOptions"
              :label="t('monitor.interval')"
              size="sm"
              @update:model-value="
                (value) => update(item, { interval_minutes: value })
              "
            />
            <span class="flex items-center gap-1.5 text-[13px] text-muted">
              <AppIcon name="clock" :size="14" class="lg:hidden" />
              {{
                item.last_checked
                  ? timeAgo(item.last_checked, locale)
                  : t('monitor.never')
              }}
            </span>
            <span class="tabular text-[13px] text-muted">
              {{
                item.kind === 'artist'
                  ? t('monitor.releases', { count: item.last_track_count })
                  : t('common.tracks', { count: item.last_track_count })
              }}
            </span>
            <UiSwitch
              :model-value="item.enabled"
              class="ml-auto lg:ml-0"
              :aria-label="
                item.enabled ? t('monitor.pause') : t('monitor.resume')
              "
              @update:model-value="(value) => update(item, { enabled: value })"
            />
          </div>
        </li>
      </TransitionGroup>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiBadge from '/src/components/ui/UiBadge.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import monitorAPI from '/src/model/monitor'
import { useUi } from '/src/model/ui'
import { timeAgo } from '/src/lib/format'
import { compareText } from '/src/lib/library'
import { useI18n } from '/src/i18n'

const { t, locale } = useI18n()
const ui = useUi()

const items = ref([])
const loading = ref(false)
const adding = ref(false)
const addError = ref('')
const newUrl = ref('')
const newInterval = ref(360)
const checking = ref(new Set())
const checkingAll = ref(false)
const filter = ref('all')
const sortKey = useLocalStorage('downtify-monitor-sort', 'created_at')
const sortDir = useLocalStorage('downtify-monitor-sort-dir', 'desc')

const INTERVALS = [15, 30, 60, 180, 360, 720, 1440, 10080, 20160, 43200]

function intervalLabel(minutes) {
  if (minutes < 60) return t('monitor.everyMinutes', { count: minutes })
  if (minutes < 1440) return t('monitor.everyHours', { count: minutes / 60 })
  if (minutes < 10080) return t('monitor.everyDays', { count: minutes / 1440 })
  if (minutes < 43200)
    return t('monitor.everyWeeks', { count: minutes / 10080 })
  return t('monitor.everyMonths', { count: Math.round(minutes / 43200) })
}

const intervalOptions = computed(() =>
  INTERVALS.map((value) => ({ value, label: intervalLabel(value) }))
)

const sortOptions = computed(() => [
  { value: 'created_at', label: t('monitor.sortAdded') },
  { value: 'name', label: t('monitor.sortName') },
  { value: 'last_checked', label: t('monitor.sortChecked') },
  { value: 'interval_minutes', label: t('monitor.sortInterval') },
  { value: 'last_track_count', label: t('monitor.sortSize') },
])

const filters = computed(() => {
  const count = (fn) => items.value.filter(fn).length
  return [
    { id: 'all', label: t('monitor.filterAll'), count: items.value.length },
    {
      id: 'playlist',
      label: t('monitor.filterPlaylists'),
      count: count((i) => i.kind !== 'artist'),
    },
    {
      id: 'artist',
      label: t('monitor.filterArtists'),
      count: count((i) => i.kind === 'artist'),
    },
    {
      id: 'paused',
      label: t('monitor.filterPaused'),
      count: count((i) => !i.enabled),
    },
  ].filter((item) => item.id === 'all' || item.count)
})

const visible = computed(() => {
  let list = items.value
  if (filter.value === 'playlist')
    list = list.filter((i) => i.kind !== 'artist')
  if (filter.value === 'artist') list = list.filter((i) => i.kind === 'artist')
  if (filter.value === 'paused') list = list.filter((i) => !i.enabled)
  const dir = sortDir.value === 'asc' ? 1 : -1
  const key = sortKey.value
  return [...list].sort((a, b) => {
    if (key === 'name') return dir * compareText(a.name, b.name)
    if (key === 'created_at' || key === 'last_checked') {
      return dir * (new Date(a[key] || 0) - new Date(b[key] || 0))
    }
    return dir * ((a[key] || 0) - (b[key] || 0))
  })
})

async function load() {
  loading.value = true
  try {
    const res = await monitorAPI.listMonitoredPlaylists()
    items.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function add() {
  addError.value = ''
  adding.value = true
  try {
    const res = await monitorAPI.addMonitoredPlaylist(
      newUrl.value.trim(),
      newInterval.value
    )
    items.value = [res.data, ...items.value]
    newUrl.value = ''
    ui.toast(t('toast.watching', { name: res.data.name }), { kind: 'success' })
  } catch (err) {
    addError.value = err?.response?.data?.detail || t('monitor.addFailed')
  } finally {
    adding.value = false
  }
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
  for (const item of items.value.filter((i) => i.enabled)) {
    await monitorAPI.checkMonitoredPlaylist(item.id).catch(() => {})
  }
  ui.toast(t('monitor.checkingAll'))
  setTimeout(() => {
    checkingAll.value = false
    load()
  }, 4000)
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
      label: item.enabled ? t('monitor.pause') : t('monitor.resume'),
      icon: item.enabled ? 'pause' : 'play',
      action: () => update(item, { enabled: !item.enabled }),
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
