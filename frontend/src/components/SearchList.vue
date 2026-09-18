<template>
  <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold tracking-tight">{{ t('search.title') }}</h1>
      <p class="mt-1 text-sm text-base-content/60">
        <template v-if="sm.searchTerm.value">
          {{ t('search.matchesFor') }}
          <span class="text-base-content/90 font-medium">
            "{{ sm.searchTerm.value }}"
          </span>
          <template
            v-if="!sm.isSearching.value && (props.data?.length || 0) > 0"
          >
            {{
              props.data.length === 1
                ? t('search.songsCount', { count: props.data.length })
                : t('search.songsCountPlural', { count: props.data.length })
            }}
          </template>
        </template>
        <template v-else>{{ t('search.typeToBegin') }}</template>
      </p>
    </div>

    <!-- Error -->
    <div
      v-if="props.error"
      class="surface rounded-2xl p-4 mb-4 flex gap-3 items-center text-sm text-error"
    >
      <Icon icon="fa6-solid:circle-exclamation" class="h-5 w-5 shrink-0" />
      <span>
        {{
          sm.errorValue.value
            ? t('search.errorWithDetail', { detail: sm.errorValue.value })
            : t('search.error')
        }}
      </span>
    </div>

    <!-- Artist top songs -->
    <div v-if="artistLoading" class="mb-8">
      <div class="skeleton h-24 rounded-2xl" />
    </div>
    <div v-else-if="props.artist" class="mb-8">
      <div class="surface rounded-2xl track-card">
        <!-- Cover -->
        <div class="track-cover">
          <img
            v-if="props.artist.cover_url"
            :src="props.artist.cover_url"
            :alt="props.artist.name"
            class="h-full w-full object-cover"
            loading="lazy"
          />
          <div
            v-else
            class="h-full w-full flex items-center justify-center text-base-content/30"
          >
            <Icon icon="fa6-solid:user" class="h-6 w-6" />
          </div>
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex flex-wrap items-center gap-2 mb-0.5">
            <span class="font-semibold truncate">
              {{ t('search.topSongsOf', { artist: props.artist.name }) }}
            </span>
            <span
              v-if="artistSourceBadge"
              class="shrink-0 gap-1"
              :class="artistSourceBadge.badge"
              :title="artistSourceBadge.label"
            >
              <Icon :icon="artistSourceBadge.icon" class="h-3 w-3" />
              {{ artistSourceBadge.label }}
            </span>
          </div>
          <p class="text-xs text-base-content/70 truncate">
            {{ props.artist.name }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2 shrink-0">
          <label
            class="inline-flex items-center gap-1.5 text-xs text-base-content/70 cursor-pointer"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-xs checkbox-primary"
              v-model="createArtistPlaylist"
              :disabled="artistQueued"
            />
            {{ t('search.createPlaylist') }}
          </label>
          <NumberSpinner
            v-model="topSongsCount"
            :min="1"
            :max="10"
            :disabled="artistQueued"
          />
          <button
            v-if="artistQueued"
            class="icon-btn text-primary cursor-default"
            :title="t('search.inQueue')"
            disabled
          >
            <Icon icon="fa6-solid:circle-check" class="h-5 w-5" />
          </button>
          <button
            v-else
            class="icon-btn text-primary hover:bg-primary/10"
            @click="downloadArtistTopSongs"
            :title="t('search.downloadTopSongs')"
          >
            <Icon icon="fa6-solid:download" class="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Albums -->
    <div v-if="sm.albumResults.value.length > 0" class="mb-8">
      <h2
        class="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-3"
      >
        {{ t('search.albumsTitle') }}
      </h2>
      <ul class="space-y-2">
        <li
          v-for="album in sm.albumResults.value"
          :key="album.album_id"
          class="surface rounded-2xl track-card"
        >
          <!-- Cover -->
          <div class="track-cover">
            <img
              v-if="album.cover_url"
              :src="album.cover_url"
              :alt="album.name"
              class="h-full w-full object-cover"
              loading="lazy"
            />
            <div
              v-else
              class="h-full w-full flex items-center justify-center text-base-content/30"
            >
              <Icon icon="fa6-solid:record-vinyl" class="h-6 w-6" />
            </div>
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5">
              <span class="font-semibold truncate">{{ album.name }}</span>
              <span
                class="badge-soft shrink-0 text-[10px] uppercase tracking-wide"
              >
                {{ releaseTypeBadge(album) }}
              </span>
            </div>
            <p class="text-xs text-base-content/70 truncate">
              {{ album.artist || t('common.unknownArtist') }}
            </p>
            <p v-if="album.year" class="text-xs text-base-content/40 truncate">
              {{ album.year }}
            </p>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <a
              v-if="album.url"
              class="icon-btn"
              :href="album.url"
              target="_blank"
              rel="noopener"
              :title="t('search.openSource')"
            >
              <Icon
                icon="fa6-solid:arrow-up-right-from-square"
                class="h-4 w-4"
              />
            </a>
            <button
              v-if="albumDownloadState(album) === 'queued'"
              class="icon-btn text-primary cursor-default"
              :title="t('search.inQueue')"
              disabled
            >
              <Icon icon="fa6-solid:circle-check" class="h-5 w-5" />
            </button>
            <button
              v-else
              class="icon-btn text-primary hover:bg-primary/10"
              @click="downloadAlbum(album)"
              :title="t('search.downloadAlbum')"
            >
              <Icon icon="fa6-solid:download" class="h-5 w-5" />
            </button>
          </div>
        </li>
      </ul>
    </div>

    <!-- Songs section label — only needed to separate from the Albums
         section above; standalone song results don't need a heading. -->
    <h2
      v-if="sm.albumResults.value.length > 0 && props.data?.length"
      class="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-3"
    >
      {{ t('search.songsTitle') }}
    </h2>

    <!-- Loading skeleton -->
    <div v-if="sm.isSearching.value" class="space-y-3">
      <div v-for="n in 5" :key="n" class="skeleton h-24 rounded-2xl" />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!props.data || props.data.length === 0"
      class="surface rounded-2xl p-12 flex flex-col items-center text-center"
    >
      <Icon
        icon="fa6-solid:magnifying-glass"
        class="h-12 w-12 text-base-content/20 mb-4"
      />
      <p class="text-base-content/50 text-sm">{{ t('search.empty') }}</p>
      <p class="text-base-content/40 text-xs mt-1">
        {{ t('search.emptyHint') }}
      </p>
    </div>

    <!-- Results -->
    <ul v-else class="space-y-2">
      <li
        v-for="(song, index) in paginatedData"
        :key="song.song_id || index"
        class="surface rounded-2xl track-card"
      >
        <!-- Cover -->
        <div class="track-cover">
          <img
            v-if="song.cover_url"
            :src="song.cover_url"
            :alt="song.name"
            class="h-full w-full object-cover"
            loading="lazy"
          />
          <div
            v-else
            class="h-full w-full flex items-center justify-center text-base-content/30"
          >
            <Icon icon="fa6-solid:music" class="h-6 w-6" />
          </div>
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-0.5">
            <span class="font-semibold truncate">{{ song.name }}</span>
            <span v-if="song.explicit" class="badge-error-soft shrink-0"
              >E</span
            >
          </div>
          <p class="text-xs text-base-content/70 truncate">
            {{ artistsOf(song) }}
          </p>
          <p
            v-if="song.album_name"
            class="text-xs text-base-content/40 truncate"
          >
            {{ song.album_name }}
            <span v-if="song.year" class="text-base-content/30">
              · {{ song.year }}
            </span>
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 shrink-0">
          <a
            v-if="song.url && song.source !== 'text_search'"
            class="icon-btn"
            :href="song.url"
            target="_blank"
            rel="noopener"
            :title="t('search.openSource')"
          >
            <Icon icon="fa6-solid:arrow-up-right-from-square" class="h-4 w-4" />
          </a>

          <button
            v-if="downloadState(song) === 'queued'"
            class="icon-btn text-primary cursor-default"
            :title="t('search.inQueue')"
            disabled
          >
            <Icon icon="fa6-solid:circle-check" class="h-5 w-5" />
          </button>
          <button
            v-else
            class="icon-btn text-primary hover:bg-primary/10"
            @click="download(song)"
            :title="t('search.download')"
          >
            <Icon icon="fa6-solid:download" class="h-5 w-5" />
          </button>
        </div>
      </li>
    </ul>

    <!-- Pagination -->
    <Pagination
      v-if="totalPages > 1"
      v-model="currentPage"
      :total-pages="totalPages"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Icon } from '@iconify/vue'

import Pagination from './Pagination.vue'
import NumberSpinner from './NumberSpinner.vue'
import { useSearchManager } from '../model/search'
import { useProgressTracker, useDownloadManager } from '../model/download'
import { useI18n } from '../i18n'

const PAGE_SIZE = 5

const props = defineProps(['data', 'error', 'artist', 'artistLoading'])
const emit = defineEmits(['download', 'download-artist-top-songs'])

const sm = useSearchManager()
const pt = useProgressTracker()
const dm = useDownloadManager()
const { t } = useI18n()

const currentPage = ref(1)
const topSongsCount = ref(5)
const artistQueued = ref(false)
const createArtistPlaylist = ref(true)

watch(
  () => props.artist,
  () => {
    topSongsCount.value = 5
    artistQueued.value = false
    createArtistPlaylist.value = true
  }
)

function downloadArtistTopSongs() {
  artistQueued.value = true
  emit('download-artist-top-songs', {
    count: topSongsCount.value,
    createPlaylist: createArtistPlaylist.value,
  })
}

// Which platform the top-songs shelf was resolved from, styled like the
// source badges on the Downloads and Playlist Monitor pages.
const ARTIST_SOURCES = {
  spotify: {
    label: t('monitor.sourceSpotify'),
    badge: 'badge-spotify',
    icon: 'fa6-brands:spotify',
  },
  youtube: {
    label: t('monitor.sourceYouTubeMusic'),
    badge: 'badge-youtube-music',
    icon: 'fa6-brands:youtube',
  },
}

const artistSourceBadge = computed(
  () => ARTIST_SOURCES[props.artist?.source] || null
)
// Albums don't have a single stable id in the shared progress tracker
// until their tracks are resolved, so "queued" is tracked locally here —
// same "click, get a checkmark, stay put" confirmation songs already get.
const queuedAlbumIds = ref(new Set())

const totalPages = computed(() =>
  Math.ceil((props.data?.length || 0) / PAGE_SIZE)
)

const paginatedData = computed(() => {
  if (!props.data) return []
  const start = (currentPage.value - 1) * PAGE_SIZE
  return props.data.slice(start, start + PAGE_SIZE)
})

watch(
  () => props.data,
  () => {
    currentPage.value = 1
  }
)

function artistsOf(song) {
  if (Array.isArray(song.artists) && song.artists.length) {
    return song.artists.join(', ')
  }
  return song.artist || t('common.unknownArtist')
}

function downloadState(song) {
  const item = pt.getBySong(song)
  if (!item) return 'idle'
  if (item.isErrored()) return 'error'
  if (item.isDownloaded()) return 'queued'
  return 'queued'
}

function download(song) {
  emit('download', song)
}

function albumDownloadState(album) {
  return queuedAlbumIds.value.has(album.album_id) ? 'queued' : 'idle'
}

function downloadAlbum(album) {
  queuedAlbumIds.value.add(album.album_id)
  dm.fromURL(album.url)
}

function releaseTypeBadge(album) {
  const type = (album.release_type || '').toLowerCase()
  if (type === 'single') return t('search.singleBadge')
  if (type === 'ep') return t('search.epBadge')
  return t('search.albumBadge')
}
</script>
