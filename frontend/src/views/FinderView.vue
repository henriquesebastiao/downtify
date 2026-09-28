<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <div class="flex flex-col gap-4">
      <PageHeader
        :title="query ? t('finder.resultsFor', { query }) : t('finder.title')"
        :subtitle="
          query
            ? finder.loading.value
              ? t('search.searching')
              : ''
            : t('finder.subtitle')
        "
      />
      <form
        role="search"
        class="flex max-w-2xl items-center gap-2"
        @submit.prevent="submit"
      >
        <span
          class="flex h-11 min-w-0 flex-1 items-center gap-2.5 rounded-[12px] border border-line-2 bg-surface pr-1.5 pl-3.5 transition-colors focus-within:border-accent"
        >
          <AppIcon name="deezer" :size="18" class="text-deezer" />
          <label for="finder-search" class="sr-only">{{
            t('finder.placeholder')
          }}</label>
          <input
            id="finder-search"
            ref="input"
            v-model="text"
            type="search"
            enterkeyhint="search"
            autocomplete="off"
            :placeholder="t('finder.placeholder')"
            class="h-full min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-faint [&::-webkit-search-cancel-button]:hidden"
          />
          <button
            v-if="text"
            type="button"
            class="flex size-8 items-center justify-center rounded-control text-faint hover:text-fg"
            :aria-label="t('common.clear')"
            @click="clear"
          >
            <AppIcon name="x" :size="16" />
          </button>
        </span>
        <UiButton
          type="submit"
          variant="primary"
          icon="search"
          :disabled="!text.trim()"
        >
          {{ t('search.searchButton') }}
        </UiButton>
      </form>
      <UiChips v-if="query" v-model="filter" :items="filters" />
    </div>

    <template v-if="!query">
      <div class="grid gap-4 md:grid-cols-3">
        <div
          v-for="tip in tips"
          :key="tip.title"
          class="flex flex-col gap-2 rounded-panel border border-line-2 bg-surface p-5"
        >
          <span
            class="flex size-10 items-center justify-center rounded-[10px]"
            :class="tip.tone"
          >
            <AppIcon :name="tip.icon" :size="20" />
          </span>
          <p class="mt-1 text-[15px] font-semibold">{{ tip.title }}</p>
          <p class="text-[13px] text-pretty text-muted">{{ tip.body }}</p>
        </div>
      </div>
      <section v-if="recent.length" class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h2 class="text-display text-lg font-semibold">
            {{ t('search.recent') }}
          </h2>
          <button
            type="button"
            class="text-[13px] font-semibold text-muted hover:text-fg"
            @click="recent = []"
          >
            {{ t('common.clear') }}
          </button>
        </div>
        <div class="flex flex-wrap gap-2">
          <RouterLink
            v-for="term in recent"
            :key="term"
            :to="{ name: 'Finder', query: { q: term } }"
            class="flex h-9 items-center gap-2 rounded-full bg-surface-2 px-3.5 text-sm text-fg-3 hover:bg-raised"
          >
            <AppIcon name="clock" :size="14" class="text-faint" />{{ term }}
          </RouterLink>
        </div>
      </section>
    </template>

    <template v-else>
      <div v-if="finder.loading.value" class="flex flex-col gap-2">
        <div v-for="n in 6" :key="n" class="flex h-16 items-center gap-3 px-3">
          <UiSkeleton class="size-11 !rounded-[8px]" />
          <div class="flex flex-1 flex-col gap-2">
            <UiSkeleton class="h-3.5 w-1/3" />
            <UiSkeleton class="h-3 w-1/5" />
          </div>
        </div>
      </div>

      <UiEmpty
        v-else-if="finder.error.value"
        icon="alert"
        :title="t('search.failed')"
        :body="finder.error.value"
      >
        <UiButton icon="refresh" @click="finder.searchFor(query)">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>

      <UiEmpty
        v-else-if="!hasResults"
        icon="search"
        :title="t('search.noResults')"
        :body="t('search.noResultsHint')"
      />

      <template v-else>
        <section
          v-if="show('songs') && finder.songs.value.length"
          class="flex flex-col gap-3"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('search.songs') }}
          </h2>
          <div class="-mx-3 flex flex-col">
            <TrackDownPlay
              v-for="(song, i) in visibleSongs"
              :key="song.song_id || song.url"
              :song="song"
              :index="i"
              :queue="songQueue"
              :to="browseLocation('song', song)"
            />
          </div>
          <button
            v-if="
              filter === 'all' &&
              finder.songs.value.length > visibleSongs.length
            "
            type="button"
            class="self-start text-[13px] font-semibold text-muted hover:text-fg"
            @click="filter = 'songs'"
          >
            {{ t('search.showAllSongs', { count: finder.songs.value.length }) }}
          </button>
        </section>

        <section
          v-if="show('albums') && finder.albums.value.length"
          class="flex flex-col gap-4"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('search.albums') }}
          </h2>
          <div
            class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
          >
            <ReleaseCard
              v-for="album in visibleAlbums"
              :key="album.album_id"
              :release="album"
              :to="browseLocation('album', album)"
            />
          </div>
        </section>

        <section
          v-if="show('artists') && finder.artists.value.length"
          class="flex flex-col gap-4"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('search.artists') }}
          </h2>
          <div
            class="grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
          >
            <ReleaseCard
              v-for="artist in visibleArtists"
              :key="artist.artist_id"
              :release="artist"
              :to="browseLocation('artist', artist)"
              round
            />
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
// The Finder's first page: the same shape as Search (tips and recent
// searches, then songs/albums/artists with filter chips), but searching
// Deezer alone, with its own box. A result opens the column view
// (FinderBrowseView) instead of the Link page.
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import TrackDownPlay from '/src/components/library/TrackDownPlay.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import { useFinder } from '/src/model/finder'
import { useLibrary } from '/src/model/library'
import { browseLocation } from '/src/lib/finder'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const finder = useFinder()
const library = useLibrary()
const filter = ref('all')
const recent = useLocalStorage('downtify-finder-recent-searches', [])
const input = ref(null)

const query = computed(() => String(route.query.q || '').trim())
const text = ref(query.value)

watch(
  query,
  (value) => {
    text.value = value
    filter.value = 'all'
    if (!value) return
    recent.value = [
      value,
      ...recent.value.filter((term) => term !== value),
    ].slice(0, 10)
    if (value !== finder.query.value || finder.error.value) {
      finder.searchFor(value)
    }
  },
  { immediate: true }
)

function submit() {
  const term = text.value.trim()
  if (!term) return
  router.push({ name: 'Finder', query: { q: term } })
  input.value?.blur()
}

function clear() {
  text.value = ''
  input.value?.focus()
}

const filters = computed(() => [
  { id: 'all', label: t('search.all') },
  { id: 'songs', label: t('search.songs'), count: finder.songs.value.length },
  {
    id: 'albums',
    label: t('search.albums'),
    count: finder.albums.value.length,
  },
  {
    id: 'artists',
    label: t('search.artists'),
    count: finder.artists.value.length,
  },
])

function show(section) {
  return filter.value === 'all' || filter.value === section
}

const hasResults = computed(
  () =>
    finder.songs.value.length ||
    finder.albums.value.length ||
    finder.artists.value.length
)

const visibleSongs = computed(() =>
  filter.value === 'all' ? finder.songs.value.slice(0, 8) : finder.songs.value
)
const visibleAlbums = computed(() =>
  filter.value === 'all' ? finder.albums.value.slice(0, 6) : finder.albums.value
)
const visibleArtists = computed(() =>
  filter.value === 'all'
    ? finder.artists.value.slice(0, 6)
    : finder.artists.value
)

// Downloaded songs play from the library, in the results' order.
const songQueue = computed(() =>
  playableQueue(finder.songs.value, library.findTrack)
)

const tips = computed(() => [
  {
    icon: 'deezer',
    tone: 'bg-deezer/12 text-deezer',
    title: t('finder.tipSearchTitle'),
    body: t('finder.tipSearchBody'),
  },
  {
    icon: 'columns',
    tone: 'bg-accent/12 text-accent',
    title: t('finder.tipColumnsTitle'),
    body: t('finder.tipColumnsBody'),
  },
  {
    icon: 'download',
    tone: 'bg-spotify/12 text-spotify',
    title: t('finder.tipDownloadTitle'),
    body: t('finder.tipDownloadBody'),
  },
])
</script>
