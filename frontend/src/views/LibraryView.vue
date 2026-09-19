<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('library.title')" :subtitle="summary">
      <UiButton
        v-if="library.tracks.value.length"
        variant="ghost"
        icon="wand"
        :to="{ name: 'Upgrade' }"
      >
        <span class="max-sm:sr-only">{{ t('library.upgrade') }}</span>
      </UiButton>
      <UiButton
        variant="ghost"
        icon="refresh"
        :loading="library.loading.value"
        @click="library.load({ force: true })"
      >
        <span class="max-sm:sr-only">{{ t('common.refresh') }}</span>
      </UiButton>
    </PageHeader>

    <UiTabs :items="tabs" :model-value="tab" />

    <div class="flex flex-wrap items-center gap-2">
      <label
        class="flex h-10 min-w-0 flex-1 basis-56 items-center gap-2.5 rounded-control border border-line-2 bg-surface px-3 focus-within:border-accent sm:max-w-xs"
      >
        <AppIcon name="filter" :size="16" class="text-faint" />
        <span class="sr-only">{{ t('library.filterPlaceholder') }}</span>
        <input
          v-model="filter"
          type="search"
          :placeholder="t('library.filterPlaceholder')"
          class="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
        />
      </label>
      <UiChips
        v-if="tab === 'tracks' && formatChips.length > 2"
        v-model="format"
        :items="formatChips"
        class="max-w-full"
      />
      <div class="ml-auto flex items-center gap-2">
        <UiSelect
          v-if="tab !== 'tracks'"
          v-model="sortKey"
          :options="sortOptions"
          :label="t('library.sortBy')"
          icon="sort"
        />
        <UiSegmented
          v-if="tab !== 'tracks'"
          v-model="view"
          :options="[
            { value: 'grid', icon: 'grid', label: t('library.viewGrid') },
            { value: 'list', icon: 'list', label: t('library.viewList') },
          ]"
        />
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="!library.loaded.value && library.loading.value"
      class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6"
    >
      <div v-for="n in 12" :key="n" class="flex flex-col gap-2.5">
        <UiSkeleton class="aspect-square !rounded-cover" />
        <UiSkeleton class="h-4 w-3/4" />
        <UiSkeleton class="h-3 w-1/2" />
      </div>
    </div>

    <UiEmpty
      v-else-if="library.error.value && !library.tracks.value.length"
      icon="alert"
      :title="t('library.loadFailed')"
      :body="t('library.loadFailedHint')"
    >
      <UiButton icon="refresh" @click="library.load({ force: true })">
        {{ t('common.retry') }}
      </UiButton>
    </UiEmpty>

    <UiEmpty
      v-else-if="
        !library.tracks.value.length && !library.playlists.value.length
      "
      icon="library"
      :title="t('library.emptyTitle')"
      :body="t('library.emptyBody')"
    >
      <UiButton variant="primary" icon="search" @click="ui.focusSearch()">
        {{ t('library.emptyAction') }}
      </UiButton>
    </UiEmpty>

    <UiEmpty
      v-else-if="!items.length"
      icon="filter"
      :title="t('library.noMatches')"
      :body="t('library.noMatchesHint')"
    >
      <UiButton variant="ghost" @click="clearFilters">{{
        t('library.clearFilters')
      }}</UiButton>
    </UiEmpty>

    <!-- Tracks -->
    <template v-else-if="tab === 'tracks'">
      <SelectionBar
        :count="selected.size"
        :total="items.length"
        :zipping="zipping"
        @select-all="selected = new Set(items.map((track) => track.file))"
        @clear="selected = new Set()"
        @play="actions.play(selectedTracks, 0, libraryContext)"
        @enqueue="actions.enqueue(selectedTracks)"
        @zip="zipSelected"
        @delete="deleteSelected"
      />
      <div class="flex flex-wrap items-center gap-2">
        <UiButton
          variant="primary"
          icon="play"
          @click="actions.play(items, 0, libraryContext)"
        >
          {{ t('actions.playAll') }}
        </UiButton>
        <UiButton
          variant="secondary"
          icon="shuffle"
          @click="actions.play(items, 0, libraryContext, { shuffled: true })"
        >
          {{ t('actions.shuffle') }}
        </UiButton>
        <span class="tabular ml-auto text-[13px] text-muted">
          {{ t('common.tracks', { count: items.length }) }}
        </span>
      </div>
      <TrackList
        v-model:selected="selected"
        v-model:sort="trackSort"
        :tracks="items"
        :context="libraryContext"
      />
    </template>

    <!-- Albums / artists / playlists: grid -->
    <div
      v-else-if="view === 'grid'"
      class="grid grid-cols-2 gap-x-4 gap-y-7 xs:gap-x-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6 min-[1900px]:grid-cols-7"
    >
      <MediaTile
        v-for="item in items"
        :key="item.key"
        v-bind="tileProps(item)"
        class="[contain-intrinsic-size:auto_260px] [content-visibility:auto]"
        @play="playItem(item)"
      >
        <template
          v-if="tab === 'playlists' && item.batch?.missing_count"
          #badge
        >
          <span
            class="absolute right-2.5 bottom-2.5 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-warn backdrop-blur"
          >
            {{
              t('playlists.missingShort', { count: item.batch.missing_count })
            }}
          </span>
        </template>
      </MediaTile>
    </div>

    <!-- Albums / artists / playlists: list -->
    <div v-else class="-mx-3 flex flex-col">
      <MediaRow
        v-for="item in items"
        :key="item.key"
        v-bind="tileProps(item)"
        :aside="asideFor(item)"
        class="[contain-intrinsic-size:auto_72px] [content-visibility:auto]"
        @play="playItem(item)"
      >
        <template v-if="tab === 'playlists'" #meta>
          <PlaylistStatus :playlist="item" class="w-56" />
        </template>
        <template v-if="tab === 'playlists'" #actions>
          <UiMenu
            :items="playlistMenu(item)"
            :label="t('common.more')"
            size="sm"
          />
        </template>
      </MediaRow>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import UiSegmented from '/src/components/ui/UiSegmented.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import MediaRow from '/src/components/library/MediaRow.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import PlaylistStatus from '/src/components/library/PlaylistStatus.vue'
import SelectionBar from '/src/components/library/SelectionBar.vue'
import TrackList from '/src/components/library/TrackList.vue'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useTrackActions } from '/src/model/trackActions'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useUi } from '/src/model/ui'
import { albumKey, artistKey, filterItems, sortItems } from '/src/lib/library'
import { formatBytes, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const ui = useUi()

const TABS = ['albums', 'artists', 'playlists', 'tracks']
const lastTab = useLocalStorage('downtify-library-tab', 'albums')
const tab = computed(() => {
  const requested = String(route.params.tab || '')
  return TABS.includes(requested) ? requested : lastTab.value
})
watch(tab, (value) => (lastTab.value = value), { immediate: true })
if (!route.params.tab) {
  router.replace({ name: 'Library', params: { tab: tab.value } })
}

const views = useLocalStorage('downtify-library-views', {
  albums: 'grid',
  artists: 'grid',
  playlists: 'grid',
})
const view = computed({
  get: () => views.value[tab.value] || 'grid',
  set: (value) => (views.value = { ...views.value, [tab.value]: value }),
})

const sorts = useLocalStorage('downtify-library-sorts', {
  albums: 'added',
  artists: 'title',
  playlists: 'added',
})
const sortKey = computed({
  get: () => sorts.value[tab.value] || 'added',
  set: (value) => (sorts.value = { ...sorts.value, [tab.value]: value }),
})
const trackSort = useLocalStorage('downtify-library-track-sort', {
  key: 'added',
  dir: 'asc',
})

const filter = ref('')
const format = ref('all')
const selected = ref(new Set())
const zipping = ref(false)
watch(tab, () => {
  filter.value = ''
  format.value = 'all'
  selected.value = new Set()
})

const tabs = computed(() => [
  {
    id: 'albums',
    label: t('library.albums'),
    count: library.albums.value.length,
    to: { name: 'Library', params: { tab: 'albums' } },
  },
  {
    id: 'artists',
    label: t('library.artists'),
    count: library.artists.value.length,
    to: { name: 'Library', params: { tab: 'artists' } },
  },
  {
    id: 'playlists',
    label: t('library.playlists'),
    count: library.playlists.value.length,
    to: { name: 'Library', params: { tab: 'playlists' } },
  },
  {
    id: 'tracks',
    label: t('library.tracks'),
    count: library.tracks.value.length,
    to: { name: 'Library', params: { tab: 'tracks' } },
  },
])

const summary = computed(() => {
  if (!library.loaded.value) return ''
  return [
    t('common.tracks', { count: library.tracks.value.length }),
    t('common.albums', { count: library.albums.value.length }),
    t('common.artists', { count: library.artists.value.length }),
    formatBytes(library.totalSize.value),
  ].join(' · ')
})

const sortOptions = computed(() => {
  const base = [
    { value: 'added', label: t('library.sortRecent') },
    { value: 'title', label: t('library.sortName') },
  ]
  if (tab.value === 'albums') {
    base.push(
      { value: 'artist', label: t('library.sortArtist') },
      { value: 'year', label: t('library.sortYear') }
    )
  }
  base.push({ value: 'count', label: t('library.sortTrackCount') })
  return base
})

const formatChips = computed(() => {
  const counts = new Map()
  for (const track of library.tracks.value) {
    counts.set(track.format, (counts.get(track.format) || 0) + 1)
  }
  return [
    { id: 'all', label: t('library.allFormats') },
    ...[...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([id, count]) => ({ id, label: id, count })),
  ]
})

const items = computed(() => {
  if (tab.value === 'tracks') {
    let list = library.tracks.value
    if (format.value !== 'all') {
      list = list.filter((track) => track.format === format.value)
    }
    list = filterItems(list, filter.value, ['title', 'artist', 'album', 'file'])
    return sortItems(list, trackSort.value.key, trackSort.value.dir)
  }
  if (tab.value === 'albums') {
    return sortItems(
      filterItems(library.albums.value, filter.value, [
        'title',
        'artist',
        'year',
      ]),
      sortKey.value
    )
  }
  if (tab.value === 'artists') {
    return sortItems(
      filterItems(library.artists.value, filter.value, ['name']),
      sortKey.value
    )
  }
  return sortItems(
    filterItems(library.playlists.value, filter.value, ['title', 'name']),
    sortKey.value
  )
})

const selectedTracks = computed(() =>
  items.value.filter((track) => selected.value.has(track.file))
)

const libraryContext = computed(() => ({
  type: 'library',
  title: t('library.allTracks'),
  route: { name: 'Library', params: { tab: 'tracks' } },
}))

const current = computed(() => player.currentTrack.value)

function tileProps(item) {
  if (tab.value === 'albums') {
    return {
      to: { name: 'Album', query: { artist: item.artist, title: item.title } },
      title: item.title,
      subtitle: [item.artist, item.year].filter(Boolean).join(' · '),
      cover: item.cover,
      name: item.title,
      icon: 'disc',
      playing:
        !!current.value &&
        albumKey(current.value.albumArtist, current.value.album) === item.key,
    }
  }
  if (tab.value === 'artists') {
    return {
      to: { name: 'Artist', query: { name: item.name } },
      title: item.name,
      subtitle: [
        item.albums.length
          ? t('common.albums', { count: item.albums.length })
          : '',
        t('common.tracks', { count: item.tracks.length }),
      ]
        .filter(Boolean)
        .join(' · '),
      cover: item.cover,
      name: item.name,
      icon: 'user',
      round: true,
      playing:
        !!current.value && artistKey(current.value.albumArtist) === item.key,
    }
  }
  return {
    to: { name: 'Playlist', query: { name: item.name } },
    title: item.title,
    subtitle: playlistSubtitle(item),
    cover: item.cover,
    covers: item.covers,
    name: item.title,
    icon: item.liked ? 'heart' : 'playlist',
    symbol: item.liked,
    playable: item.tracks.length > 0,
    playing:
      player.context.value?.type === 'playlist' &&
      player.context.value?.title === item.title,
  }
}

function playlistSubtitle(item) {
  const batch = item.batch
  if (batch?.expected_count) {
    return t('playlists.progress', {
      have: batch.downloaded_count,
      total: batch.expected_count,
    })
  }
  return t('common.tracks', { count: item.tracks.length })
}

function asideFor(item) {
  const { hours, minutes } = splitLength(item.duration)
  if (!hours && !minutes) return ''
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
}

function playItem(item) {
  if (tab.value === 'albums') {
    actions.play(item.tracks, 0, {
      type: 'album',
      title: item.title,
      subtitle: item.artist,
      cover: item.cover,
      route: {
        name: 'Album',
        query: { artist: item.artist, title: item.title },
      },
    })
  } else if (tab.value === 'artists') {
    actions.play(
      item.tracks,
      0,
      {
        type: 'artist',
        title: item.name,
        cover: item.cover,
        route: { name: 'Artist', query: { name: item.name } },
      },
      { shuffled: true }
    )
  } else {
    actions.play(item.tracks, 0, playlistActions.contextFor(item))
  }
}

function playlistMenu(item) {
  return playlistActions.menuFor(item)
}

function clearFilters() {
  filter.value = ''
  format.value = 'all'
}

async function zipSelected() {
  zipping.value = true
  await actions.downloadZip(selectedTracks.value)
  zipping.value = false
}

async function deleteSelected() {
  const deleted = await actions.remove(selectedTracks.value)
  if (deleted.length) {
    const gone = new Set(deleted)
    selected.value = new Set(
      [...selected.value].filter((file) => !gone.has(file))
    )
  }
}
</script>
