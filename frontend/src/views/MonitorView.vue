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
          class="hidden grid-cols-[minmax(0,2fr)_140px_170px_150px_110px_64px_128px] items-center gap-4 border-b border-line px-4 pb-2.5 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase lg:grid"
        >
          <span>{{
            tab === 'artist' ? t('monitor.colArtist') : t('monitor.colPlaylist')
          }}</span>
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
            class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-[12px] px-4 py-3 transition-colors hover:bg-surface lg:grid-cols-[minmax(0,2fr)_140px_170px_150px_110px_64px_128px]"
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
                  class="block max-w-full truncate text-left text-sm font-semibold hover:underline"
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
              <span class="lg:block">
                <WatchSourceBadge :source="item.source" />
              </span>
              <UiSelect
                :model-value="item.interval_minutes"
                :options="intervalOptions(t, item.interval_minutes)"
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
                  tab === 'artist'
                    ? t('monitor.releases', { count: item.last_track_count })
                    : t('common.tracks', { count: item.last_track_count })
                }}
              </span>
              <UiSwitch
                :model-value="item.enabled"
                class="ml-auto lg:ml-0"
                :aria-label="`${t('monitor.colActive')}: ${item.name}`"
                @update:model-value="
                  (value) => update(item, { enabled: value })
                "
              />
            </div>
          </li>
        </TransitionGroup>
      </template>
    </template>

    <WatchEditDialog
      :watch="editing"
      :cover="editing && tab === 'artist' ? artistCover(editing) : ''"
      @close="editing = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiSwitch from '/src/components/ui/UiSwitch.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import ReleaseFilters from '/src/components/monitor/ReleaseFilters.vue'
import WatchEditDialog from '/src/components/monitor/WatchEditDialog.vue'
import WatchSourceBadge from '/src/components/monitor/WatchSourceBadge.vue'
import { intervalOptions } from '/src/components/monitor/intervals'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import { useUi } from '/src/model/ui'
import { artistPhotoSource } from '/src/lib/artistPhotoProxy'
import { timeAgo } from '/src/lib/format'
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

const { t, locale } = useI18n()
const ui = useUi()
const route = useRoute()
const router = useRouter()

const items = ref([])
const loading = ref(false)
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

const counts = computed(() => countWatches(items.value))

// /monitor/playlists and /monitor/artists; plain /monitor opens the tab
// that has something in it.
const tab = computed(() => {
  if (route.params.tab === 'artists') return 'artist'
  if (route.params.tab === 'playlists') return 'playlist'
  return !counts.value.playlist && counts.value.artist ? 'artist' : 'playlist'
})

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
    sortDir.value
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
  }
}

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
