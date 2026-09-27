<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="t('charts.title')" :subtitle="t('charts.subtitle')" />

    <UiTabs v-if="hasData" :items="tabs" :model-value="tab" />

    <div v-if="chart.loading.value && !hasData" class="flex flex-col gap-8">
      <div class="flex flex-col gap-2">
        <div v-for="n in 6" :key="n" class="flex h-16 items-center gap-3 px-3">
          <UiSkeleton class="size-11 !rounded-[8px]" />
          <div class="flex flex-1 flex-col gap-2">
            <UiSkeleton class="h-3.5 w-1/3" />
            <UiSkeleton class="h-3 w-1/5" />
          </div>
        </div>
      </div>
      <div
        class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      >
        <div v-for="n in 6" :key="n" class="flex flex-col gap-2.5">
          <UiSkeleton class="aspect-square w-full !rounded-cover" />
          <UiSkeleton class="h-3.5 w-2/3" />
          <UiSkeleton class="h-3 w-1/3" />
        </div>
      </div>
    </div>

    <UiEmpty
      v-else-if="chart.error.value && !hasData"
      icon="alert"
      :title="t('charts.failed')"
      :body="chart.error.value"
    >
      <UiButton icon="refresh" @click="chart.load({ force: true })">{{
        t('common.retry')
      }}</UiButton>
    </UiEmpty>

    <UiEmpty v-else-if="!hasData" icon="trending" :title="t('charts.empty')" />

    <template v-else-if="tab === 'tracks'">
      <UiEmpty
        v-if="!chart.tracks.value.length"
        icon="music"
        :title="t('charts.empty')"
      />
      <TrackDownPlayList
        v-else
        :songs="chart.tracks.value"
        :queue="trackQueue"
        :collection-name="t('charts.title')"
        selectable
        :toolbar-mode="TOOLBAR_LAZY"
      />
    </template>

    <template v-else>
      <UiEmpty
        v-if="!activeReleases.length"
        icon="trending"
        :title="t('charts.empty')"
      />
      <div
        v-else
        class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      >
        <ChartTile
          v-for="(item, i) in activeReleases"
          :key="
            item.album_id ||
            item.artist_id ||
            item.playlist_id ||
            item.podcast_id
          "
          :item="item"
          :kind="RELEASE_KIND[tab]"
          :rank="i + 1"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import ChartTile from '/src/components/charts/ChartTile.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import TrackDownPlayList, {
  TOOLBAR_LAZY,
} from '/src/components/library/TrackDownPlayList.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import UiTabs from '/src/components/ui/UiTabs.vue'
import { useCharts } from '/src/model/charts'
import { useLibrary } from '/src/model/library'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const chart = useCharts()
const library = useLibrary()

const TABS = ['tracks', 'albums', 'artists', 'playlists', 'podcasts']
const RELEASE_KIND = {
  albums: 'album',
  artists: 'artist',
  playlists: 'playlist',
  podcasts: 'podcast',
}
const lastTab = useLocalStorage('downtify-charts-tab', 'tracks')
const tab = computed(() => {
  const requested = String(route.params.tab || '')
  return TABS.includes(requested) ? requested : lastTab.value
})
watch(tab, (value) => (lastTab.value = value), { immediate: true })
if (!route.params.tab) {
  router.replace({ name: 'Charts', params: { tab: tab.value } })
}

const hasData = computed(
  () =>
    chart.tracks.value.length ||
    chart.albums.value.length ||
    chart.artists.value.length ||
    chart.playlists.value.length ||
    chart.podcasts.value.length
)

const tabs = computed(() => [
  {
    id: 'tracks',
    label: t('library.tracks'),
    count: chart.tracks.value.length,
    to: { name: 'Charts', params: { tab: 'tracks' } },
  },
  {
    id: 'albums',
    label: t('library.albums'),
    count: chart.albums.value.length,
    to: { name: 'Charts', params: { tab: 'albums' } },
  },
  {
    id: 'artists',
    label: t('library.artists'),
    count: chart.artists.value.length,
    to: { name: 'Charts', params: { tab: 'artists' } },
  },
  {
    id: 'playlists',
    label: t('library.playlists'),
    count: chart.playlists.value.length,
    to: { name: 'Charts', params: { tab: 'playlists' } },
  },
  {
    id: 'podcasts',
    label: t('nav.podcasts'),
    count: chart.podcasts.value.length,
    to: { name: 'Charts', params: { tab: 'podcasts' } },
  },
])

// The library tracks a chart track's preview/play button queues once it has
// been downloaded - the chart's own order, downloaded songs only.
const trackQueue = computed(() =>
  playableQueue(chart.tracks.value, library.findTrack)
)

const activeReleases = computed(() => {
  if (tab.value === 'albums') return chart.albums.value
  if (tab.value === 'artists') return chart.artists.value
  if (tab.value === 'playlists') return chart.playlists.value
  if (tab.value === 'podcasts') return chart.podcasts.value
  return []
})

chart.load()
</script>
