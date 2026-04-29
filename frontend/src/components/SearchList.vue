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
      <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
      <span>
        {{
          sm.errorValue.value
            ? t('search.errorWithDetail', { detail: sm.errorValue.value })
            : t('search.error')
        }}
      </span>
    </div>

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
        icon="clarity:search-line"
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
            <Icon icon="clarity:music-note-line" class="h-6 w-6" />
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
            v-if="song.url"
            class="icon-btn"
            :href="song.url"
            target="_blank"
            rel="noopener"
            :title="t('search.openOnSpotify')"
          >
            <Icon icon="clarity:pop-out-line" class="h-4 w-4" />
          </a>

          <button
            v-if="downloadState(song) === 'queued'"
            class="icon-btn text-primary cursor-default"
            :title="t('search.inQueue')"
            disabled
          >
            <Icon icon="clarity:check-circle-line" class="h-5 w-5" />
          </button>
          <button
            v-else
            class="icon-btn text-primary hover:bg-primary/10"
            @click="download(song)"
            :title="t('search.download')"
          >
            <Icon icon="clarity:download-line" class="h-5 w-5" />
          </button>
        </div>
      </li>
    </ul>

    <!-- Pagination -->
    <nav
      v-if="totalPages > 1"
      class="mt-8 flex items-center justify-center gap-1 flex-wrap"
    >
      <button
        class="icon-btn"
        :disabled="currentPage === 1"
        @click="currentPage--"
        :title="t('search.previousPage')"
      >
        <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-[-90deg]" />
      </button>
      <button
        v-for="page in totalPages"
        :key="page"
        class="h-10 min-w-[2.5rem] rounded-full px-3 text-sm font-medium transition-colors"
        :class="
          page === currentPage
            ? 'bg-primary text-primary-content shadow-glow-sm'
            : 'text-base-content/70 hover:text-base-content hover:bg-white/10'
        "
        @click="currentPage = page"
      >
        {{ page }}
      </button>
      <button
        class="icon-btn"
        :disabled="currentPage === totalPages"
        @click="currentPage++"
        :title="t('search.nextPage')"
      >
        <Icon icon="clarity:angle-line" class="h-4 w-4 rotate-90" />
      </button>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Icon } from '@iconify/vue'

import { useSearchManager } from '../model/search'
import { useProgressTracker, useDownloadManager } from '../model/download'
import { useI18n } from '../i18n'

const PAGE_SIZE = 5

const props = defineProps(['data', 'error'])
const emit = defineEmits(['download'])

const sm = useSearchManager()
const pt = useProgressTracker()
const dm = useDownloadManager()
const { t } = useI18n()

const currentPage = ref(1)

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
</script>
