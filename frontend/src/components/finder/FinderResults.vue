<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 pb-10 sm:px-6 md:pt-8 lg:px-10"
  >
    <div class="flex flex-col gap-4">
      <PageHeader
        :title="t('finder.resultsFor', { query })"
        :subtitle="finder.loading.value ? t('search.searching') : ''"
      />
      <UiChips v-model="filter" :items="filters" />
    </div>

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
        <h2 v-if="filter === 'all'" class="text-display text-xl font-semibold">
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
            filter === 'all' && finder.songs.value.length > visibleSongs.length
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
        <h2 v-if="filter === 'all'" class="text-display text-xl font-semibold">
          {{ t('search.albums') }}
        </h2>
        <div :class="GRID">
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
        <h2 v-if="filter === 'all'" class="text-display text-xl font-semibold">
          {{ t('search.artists') }}
        </h2>
        <div :class="GRID">
          <ReleaseCard
            v-for="artist in visibleArtists"
            :key="artist.artist_id"
            :release="withPhoto(artist)"
            :to="browseLocation('artist', artist)"
            round
          />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
// What a Finder search found on Deezer - songs, albums and artists, with
// All / Songs / Albums / Artists chips - for `query`, searched as soon as it
// changes. A result opens the column view (FinderBrowseView).
import { computed, ref, watch } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiChips from '../ui/UiChips.vue'
import UiEmpty from '../ui/UiEmpty.vue'
import UiSkeleton from '../ui/UiSkeleton.vue'
import PageHeader from '../library/PageHeader.vue'
import TrackDownPlay from '../library/TrackDownPlay.vue'
import ReleaseCard from '../search/ReleaseCard.vue'
import { useFinder } from '/src/model/finder'
import { useLibrary } from '/src/model/library'
import { knownArtistPhoto } from '/src/lib/artistPhotoProxy'
import { deezerImage } from '/src/lib/deezerImage'
import { browseLocation } from '/src/lib/finder'
import { playableQueue } from '/src/lib/topSongs'
import { useI18n } from '/src/i18n'

const props = defineProps({
  query: { type: String, required: true },
})

const GRID =
  'grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6'

const { t } = useI18n()
const finder = useFinder()
const library = useLibrary()
const filter = ref('all')

// The last answer is kept (model/finder.js): coming back to the same
// search shows it again rather than asking Deezer twice.
watch(
  () => props.query,
  (value) => {
    filter.value = 'all'
    if (value && (value !== finder.query.value || finder.error.value)) {
      finder.searchFor(value)
    }
  },
  { immediate: true }
)

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

// An artist result shows the photo saved in the library when there is one,
// else its Deezer picture - through the photo proxy, which relays the picture
// it's given instead of searching Deezer for the name.
function withPhoto(artist) {
  const photo = knownArtistPhoto(artist.name, deezerImage(artist.cover_url))
  return { ...artist, cover_url: photo.cover }
}

// Downloaded songs play from the library, in the results' order.
const songQueue = computed(() =>
  playableQueue(finder.songs.value, library.findTrack)
)
</script>
